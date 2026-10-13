#!/usr/bin/env python3
"""Card Wars community server.

A small replacement for the game's online server: accounts, cloud saves,
multiplayer (fighting other players' saved decks), leaderboards and weekly
tournaments. Python 3.9+ standard library only; data lives in one SQLite file.

The HTTP API mirrors what the client code in shishkabob27/CardWars expects
(SQServer.cs, SQWebFileServer.cs, SocialManager.cs, AuthScreenController.cs,
Multiplayer/*.cs). The client only speaks plain HTTP (no modern TLS), so run
this on port 80 behind nothing.

Usage:
    python3 cardwars_server.py [--host 0.0.0.0] [--port 80] [--db cardwars.db]
"""

import argparse
import base64
import datetime as dt
import gzip
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote_plus, urlsplit

# Reported to the client as the "server version". The client forces an update
# when this is newer than its own version (1.12.9), so keep it low.
SERVER_VERSION = "1.0.0"

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,24}$")
MP_NAME_MAX = 24
SESSION_COOKIE = "sessionid"
# How long after a successful login an IP may claim that account's session.
AUTH_BIND_WINDOW = 6 * 3600
MATCH_TTL = 30 * 60
LOGIN_FAILURE_LIMIT = 20  # per IP per 10 minutes
TOURNAMENT_EPOCH = dt.datetime(2020, 1, 6, tzinfo=dt.timezone.utc)  # a Monday
TOURNAMENT_LENGTH = dt.timedelta(days=7)

log = logging.getLogger("cardwars")


# ---------------------------------------------------------------- storage --

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    pw_salt TEXT NOT NULL,
    pw_hash TEXT NOT NULL,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS saves (
    username TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    etag TEXT NOT NULL,
    updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    sid TEXT PRIMARY KEY,
    username TEXT,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS recent_auth (
    ip TEXT NOT NULL,
    username TEXT NOT NULL,
    ts REAL NOT NULL,
    PRIMARY KEY (ip, username)
);
CREATE TABLE IF NOT EXISTS mp_players (
    username TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    icon TEXT NOT NULL DEFAULT '',
    deck TEXT NOT NULL DEFAULT '',
    deck_rank REAL NOT NULL DEFAULT 0,
    landscapes TEXT NOT NULL DEFAULT '',
    leader TEXT NOT NULL DEFAULT '',
    leader_level INTEGER NOT NULL DEFAULT 1,
    level INTEGER NOT NULL DEFAULT 1,
    trophies INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    streak INTEGER NOT NULL DEFAULT 0,
    prev_rank INTEGER NOT NULL DEFAULT 0,
    last_notified REAL NOT NULL DEFAULT 0,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS matches (
    id TEXT PRIMARY KEY,
    attacker TEXT NOT NULL,
    defender TEXT NOT NULL,
    wager_win INTEGER NOT NULL,
    wager_lose INTEGER NOT NULL,
    streak_bonus INTEGER NOT NULL,
    created REAL NOT NULL,
    expires REAL NOT NULL,
    finished REAL,
    attacker_won INTEGER,
    attacker_change INTEGER,
    defender_change INTEGER
);
CREATE INDEX IF NOT EXISTS matches_attacker ON matches(attacker, finished);
CREATE INDEX IF NOT EXISTS matches_defender ON matches(defender, finished);
CREATE TABLE IF NOT EXISTS rewards (
    username TEXT NOT NULL,
    tournament_id INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    redeemed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (username, tournament_id)
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)
        self.lock = threading.RLock()

    def one(self, sql, *args):
        with self.lock:
            return self.db.execute(sql, args).fetchone()

    def all(self, sql, *args):
        with self.lock:
            return self.db.execute(sql, args).fetchall()

    def run(self, sql, *args):
        with self.lock:
            return self.db.execute(sql, args)


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 200_000).hex()


def iso(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def current_tournament(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    tid = int((now - TOURNAMENT_EPOCH) / TOURNAMENT_LENGTH)
    end = TOURNAMENT_EPOCH + TOURNAMENT_LENGTH * (tid + 1)
    return tid, end


# ------------------------------------------------------------------ server --

class CardWarsServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr, store):
        super().__init__(addr, Handler)
        self.store = store
        self.login_failures = {}
        self.failures_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    server_version = "CardWarsServer/1.0"
    protocol_version = "HTTP/1.0"

    # -- plumbing ---------------------------------------------------------

    @property
    def store(self):
        return self.server.store

    def log_message(self, fmt, *args):
        log.info("%s %s", self.client_address[0], fmt % args)

    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_PUT(self):
        self.dispatch("PUT")

    def do_DELETE(self):
        self.dispatch("DELETE")

    def dispatch(self, method):
        self.extra_headers = []
        split = urlsplit(self.path)
        # The client builds URLs like "http://host/" + "/persist/...", so
        # collapse repeated slashes.
        self.route = re.sub(r"/+", "/", split.path).strip("/")
        self.query = {k: v[0] for k, v in parse_qs(split.query, keep_blank_values=True).items()}
        length = int(self.headers.get("Content-Length") or 0)
        self.body = self.rfile.read(length) if length > 0 else b""
        self.form = {}
        if method == "POST" and self.body:
            self.form = {k: v[0] for k, v in parse_qs(self.body.decode("utf-8", "replace"), keep_blank_values=True).items()}
        self.session = self.load_session()
        try:
            handled = self.handle_route(method)
        except Exception:
            log.exception("error handling %s %s", method, self.path)
            self.send_json({"success": False, "error": "Server error"}, 500)
            return
        if not handled:
            self.send_json({"success": False, "error": "Not found"}, 404)

    def load_session(self):
        sid = None
        for part in (self.headers.get("Cookie") or "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == SESSION_COOKIE and re.fullmatch(r"[0-9a-f]{32}", value):
                sid = value
        if sid is None:
            # Stored only once it is tied to an account (see claim()), so
            # random visitors don't fill the database.
            sid = secrets.token_hex(16)
            self.extra_headers.append(("Set-Cookie", "%s=%s; Path=/" % (SESSION_COOKIE, sid)))
            return {"sid": sid, "username": None}
        row = self.store.one("SELECT username FROM sessions WHERE sid=?", sid)
        return {"sid": sid, "username": row["username"] if row else None}

    def send_raw(self, body, status=200, content_type="text/plain; charset=utf-8", headers=()):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in list(headers) + self.extra_headers:
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_json(self, obj, status=200):
        self.send_raw(json.dumps(obj).encode("utf-8"), status, "application/json")

    def send_text(self, text, status=200):
        self.send_raw(text.encode("utf-8"), status)

    def send_gzip(self, text, status=200, headers=()):
        # Files under /persist are always gunzipped by the client.
        self.send_raw(gzip.compress(text.encode("utf-8")), status, "application/octet-stream", headers)

    # -- identity ----------------------------------------------------------

    def remember_auth(self, username):
        self.store.run(
            "INSERT OR REPLACE INTO recent_auth (ip, username, ts) VALUES (?, ?, ?)",
            self.client_address[0], username, time.time())

    def claim(self, username):
        """Bind this session to `username` if allowed. Returns True if the
        session now belongs to that player."""
        if not username:
            return False
        if self.session["username"] == username:
            return True
        if self.session["username"] is not None:
            return False
        # Only the account most recently logged into from this address, so
        # two players behind the same router can't take each other's saves.
        row = self.store.one(
            "SELECT username, ts FROM recent_auth WHERE ip=? ORDER BY ts DESC LIMIT 1", self.client_address[0])
        if row is None or row["username"] != username or time.time() - row["ts"] > AUTH_BIND_WINDOW:
            return False
        self.store.run("INSERT OR REPLACE INTO sessions (sid, username, created) VALUES (?, ?, ?)",
                       self.session["sid"], username, time.time())
        self.session["username"] = username
        return True

    def me(self):
        return self.session["username"]

    # -- routing -----------------------------------------------------------

    def handle_route(self, method):
        r = self.route
        parts = r.split("/") if r else []
        if not parts:
            self.send_text("Card Wars server is running.\n")
            return True
        head = parts[0]
        if head == "account":
            return self.route_account(parts[1:])
        if head == "persist":
            return self.route_persist(method, parts[1:])
        if head == "multiplayer":
            return self.route_multiplayer(method, parts[1:])
        if head == "billing":
            if parts[1:2] in (["getPurchases"], ["get_unconfirmed_hard_currency"]):
                self.send_json({"success": True, "data": []})
            else:
                self.send_json({"success": False, "error": "Purchases are not supported"})
            return True
        if head == "time":
            now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            self.send_json({"success": True, "data": {"server_time": now}})
            return True
        if head == "static":
            # No content patches: a 404 makes the client skip patching.
            return False
        return False

    # -- accounts ----------------------------------------------------------

    def too_many_failures(self):
        ip = self.client_address[0]
        now = time.time()
        with self.server.failures_lock:
            recent = [t for t in self.server.login_failures.get(ip, []) if now - t < 600]
            self.server.login_failures[ip] = recent
            return len(recent) >= LOGIN_FAILURE_LIMIT

    def note_failure(self):
        with self.server.failures_lock:
            self.server.login_failures.setdefault(self.client_address[0], []).append(time.time())

    def route_account(self, parts):
        action = parts[0] if parts else ""
        user = self.query.get("user", "")
        password = self.query.get("pass", "")

        if action == "exists":
            # Plain "true"/"false" (AuthScreenController.OnLoginDone).
            row = self.store.one("SELECT 1 FROM users WHERE username=?", user)
            self.send_text("true" if row else "false")
            return True

        if action == "create":
            if not USERNAME_RE.match(user):
                self.send_json({"success": False, "message":
                                "Usernames need 3-24 letters, numbers, dots, dashes or underscores."})
                return True
            if len(password) < 4:
                self.send_json({"success": False, "message": "Please use a password of at least 4 characters."})
                return True
            if self.store.one("SELECT 1 FROM users WHERE username=?", user):
                self.send_json({"success": False, "message": "That username is already taken."})
                return True
            salt = secrets.token_hex(16)
            self.store.run("INSERT INTO users (username, pw_salt, pw_hash, created) VALUES (?, ?, ?, ?)",
                           user, salt, hash_password(password, salt), time.time())
            log.info("created account %s", user)
            self.remember_auth(user)
            self.send_json({"success": True})
            return True

        if action == "auth":
            if self.too_many_failures():
                self.send_json({"success": False, "message": "Too many attempts. Try again in a few minutes."})
                return True
            row = self.store.one("SELECT pw_salt, pw_hash FROM users WHERE username=?", user)
            if row is None or not hmac.compare_digest(row["pw_hash"], hash_password(password, row["pw_salt"])):
                self.note_failure()
                self.send_json({"success": False, "message": "Wrong username or password."})
                return True
            self.remember_auth(user)
            self.send_json({"success": True})
            return True

        if action == "preAuth":
            self.send_json({"success": True, "data": {"nonce": secrets.token_hex(8)}})
            return True

        if action in ("gcAuth", "fbTokenAuth"):
            # The PC port treats a "Network error" reply here as "use the
            # account from the login screen" (Session.Authorizing.OnUpdate).
            self.send_json({"success": False, "error": "Network error"})
            return True

        if action == "check_id":
            self.send_json({"success": False})
            return True
        return False

    # -- saves (/persist) --------------------------------------------------

    def route_persist(self, method, parts):
        if parts == ["version.txt"]:
            self.send_gzip(SERVER_VERSION)
            return True
        if len(parts) == 2 and parts[1] == "game":
            return self.handle_game(method, parts[0])
        if parts and parts[0] == "messages_received_ids":
            self.send_gzip("[]")
            return True
        if parts and parts[0] == "messages_get":
            return False
        if parts and parts[0] in ("user_info", "user_add_facebook"):
            self.send_gzip("{}")
            return True
        if parts and parts[0].startswith("friends_"):
            self.send_gzip("[]")
            return True
        return False

    def handle_game(self, method, username):
        owner = self.claim(username)
        if method == "GET":
            row = self.store.one("SELECT data, etag FROM saves WHERE username=?", username)
            if row is None:
                # 404 = no cloud save yet; the client keeps its local save.
                self.send_raw(b"", 404)
                return True
            self.send_gzip(row["data"], headers=[("ETag", row["etag"])])
            return True

        if method == "PUT":
            if not owner:
                log.warning("rejected save for %s from %s", username, self.client_address[0])
                self.send_json({"success": False, "error": "Not logged in as this player"}, 403)
                return True
            data = self.decode_save(self.body)
            if data is None:
                self.send_json({"success": False, "error": "Corrupt save"}, 400)
                return True
            udid = (self.headers.get("X-UDID") or "").strip()
            counter = int(time.time() * 1000)
            etag = "%d-%s" % (counter, hashlib.md5(udid.encode("utf-8")).hexdigest()) if udid else str(counter)
            self.store.run(
                "INSERT OR REPLACE INTO saves (username, data, etag, updated) VALUES (?, ?, ?, ?)",
                username, data, etag, time.time())
            self.send_raw(b'{"success": true}', 200, "application/json", [("ETag", etag)])
            return True

        if method == "DELETE":
            if not owner:
                self.send_json({"success": False}, 403)
                return True
            self.store.run("DELETE FROM saves WHERE username=?", username)
            self.send_json({"success": True})
            return True
        return False

    @staticmethod
    def decode_save(body):
        """The client uploads "username=..&score=..&data=<base64(gzip(json))>"
        (TFWebFileServer.SaveFile). Return the JSON text, or None."""
        try:
            text = body.decode("utf-8")
            if text.startswith("data="):
                payload = text[len("data="):]
            else:
                idx = text.rfind("&data=")
                if idx < 0:
                    return None
                payload = text[idx + len("&data="):]
            raw = gzip.decompress(base64.b64decode(payload))
            data = raw.decode("utf-8")
            json.loads(data)
            return data
        except Exception:
            log.exception("could not decode save")
            return None

    # -- multiplayer -------------------------------------------------------

    def mp_row(self, username):
        return self.store.one("SELECT * FROM mp_players WHERE username=?", username)

    @staticmethod
    def mp_public(row):
        return {"name": row["name"], "icon": row["icon"], "leader": row["leader"],
                "level": row["leader_level"], "trophies": row["trophies"]}

    def rank_of(self, row):
        better = self.store.one("SELECT COUNT(*) AS n FROM mp_players WHERE trophies > ?", row["trophies"])
        return better["n"] + 1

    def leaderboard_entry(self, row, rank):
        return {"rank": rank, "prev_rank": row["prev_rank"], "player_name": row["name"], "icon": row["icon"],
                "leader": row["leader"], "leader_level": row["leader_level"], "trophies": row["trophies"],
                "wins": row["wins"], "losses": row["losses"]}

    def route_multiplayer(self, method, parts):
        self.settle_tournaments()
        head = parts[0] if parts else ""
        rest = parts[1:]

        if head == "player" and rest:
            username = unquote_plus(rest[0])
            self.claim(username)
            row = self.mp_row(username)
            if row is None:
                return False  # 404 = no multiplayer profile yet
            self.send_json(self.mp_public(row))
            return True

        if head == "new_player":
            me = self.me()
            if not me:
                self.send_json({"success": False, "error": "Not logged in"}, 403)
                return True
            name = self.form.get("name", "").strip()[:MP_NAME_MAX]
            if not name:
                self.send_json({"success": False}, 403)
                return True
            clash = self.store.one("SELECT username FROM mp_players WHERE name=? COLLATE NOCASE", name)
            if clash and clash["username"] != me:
                self.send_json({"success": False, "error": "Name taken"}, 403)
                return True
            f = self.form
            if self.mp_row(me):
                self.store.run(
                    "UPDATE mp_players SET name=?, icon=?, deck=?, deck_rank=?, landscapes=?, leader=?, "
                    "leader_level=?, level=? WHERE username=?",
                    name, f.get("icon", ""), f.get("deck", ""), to_float(f.get("deck_rank")),
                    f.get("landscapes", ""), f.get("leader", ""), to_int(f.get("leader_level"), 1),
                    to_int(f.get("level"), 1), me)
            else:
                self.store.run(
                    "INSERT INTO mp_players (username, name, icon, deck, deck_rank, landscapes, leader, "
                    "leader_level, level, created) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    me, name, f.get("icon", ""), f.get("deck", ""), to_float(f.get("deck_rank")),
                    f.get("landscapes", ""), f.get("leader", ""), to_int(f.get("leader_level"), 1),
                    to_int(f.get("level"), 1), time.time())
            self.send_json({"success": True, "data": self.mp_public(self.mp_row(me))})
            return True

        if head == "update_player":
            me = self.me()
            row = self.mp_row(me) if me else None
            if row is None:
                self.send_json({"success": False}, 403 if not me else 404)
                return True
            name = (self.form.get("name") or row["name"]).strip()[:MP_NAME_MAX]
            clash = self.store.one("SELECT username FROM mp_players WHERE name=? COLLATE NOCASE", name)
            if clash and clash["username"] != me:
                self.send_json({"success": False, "error": "Name taken"}, 403)
                return True
            self.store.run("UPDATE mp_players SET name=?, icon=?, level=? WHERE username=?",
                           name, self.form.get("icon", row["icon"]), to_int(self.form.get("level"), row["level"]), me)
            self.send_json({"success": True})
            return True

        if head == "update_deck":
            username = self.form.get("name", "")
            if not self.claim(username) or self.mp_row(username) is None:
                self.send_json({"success": False}, 403)
                return True
            f = self.form
            self.store.run(
                "UPDATE mp_players SET deck=?, deck_rank=?, landscapes=?, leader=?, leader_level=? WHERE username=?",
                f.get("deck", ""), to_float(f.get("deck_rank")), f.get("landscapes", ""), f.get("leader", ""),
                to_int(f.get("leader_level"), 1), username)
            self.send_json({"success": True})
            return True

        if head == "matchmake":
            return self.route_matchmake(rest)

        if head == "player_record" and rest:
            return self.player_record(unquote_plus(rest[0]))

        if head == "record":
            return self.route_record(rest)

        if head == "active_leaderboard":
            return self.route_leaderboard(rest)

        if head == "tournament":
            return self.route_tournament(method, rest)
        return False

    # matchmaking

    def route_matchmake(self, rest):
        action = rest[0] if rest else ""
        if action == "find":
            username = self.form.get("name", "")
            if not self.claim(username):
                self.send_json({"success": False}, 403)
                return True
            me = self.mp_row(username)
            if me is None:
                return False
            opponents = self.store.all(
                "SELECT * FROM mp_players WHERE username != ? AND deck != '' "
                "ORDER BY ABS(trophies - ?) LIMIT 10", username, me["trophies"])
            if not opponents:
                log.info("no opponents for %s", username)
                return False
            opp = secrets.choice(opponents)
            diff = opp["trophies"] - me["trophies"]
            wager_win = clamp(20 + diff // 20, 5, 40)
            wager_lose = clamp(15 - diff // 25, 5, 30)
            streak_bonus = min(me["streak"] * 2, 10)
            match_id = uuid.uuid4().hex
            now = time.time()
            self.store.run(
                "INSERT INTO matches (id, attacker, defender, wager_win, wager_lose, streak_bonus, created, expires) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                match_id, username, opp["username"], wager_win, wager_lose, streak_bonus, now, now + MATCH_TTL)
            self.send_json({
                "match_id": match_id, "name": opp["name"], "icon": opp["icon"], "landscapes": opp["landscapes"],
                "leader": opp["leader"], "leader_level": opp["leader_level"], "wager_win": wager_win,
                "wager_lose": wager_lose, "streak": me["streak"], "streak_bonus": streak_bonus,
                "expiration_date": iso(now + MATCH_TTL)})
            return True

        if action == "start":
            match = self.store.one("SELECT * FROM matches WHERE id=?", self.form.get("match_id", ""))
            if match is None or not self.claim(match["attacker"]):
                return False
            opp = self.mp_row(match["defender"])
            if opp is None:
                return False
            # Raw body: the opponent's deck exactly as uploaded (base64).
            self.send_text(opp["deck"])
            return True

        if action == "complete":
            match = self.store.one("SELECT * FROM matches WHERE id=?", self.form.get("match_id", ""))
            if match is None or not self.claim(match["attacker"]):
                return False
            attacker = self.mp_row(match["attacker"])
            if match["finished"] is not None:
                self.send_json({"success": True, "data": {"trophies": attacker["trophies"]}})
                return True
            lost = self.form.get("loss", "").lower() == "true"
            if lost:
                a_change = -match["wager_lose"]
                d_change = match["wager_lose"] // 2
                self.store.run("UPDATE mp_players SET trophies=MAX(0, trophies+?), losses=losses+1, streak=0 "
                               "WHERE username=?", a_change, match["attacker"])
                self.store.run("UPDATE mp_players SET trophies=trophies+? WHERE username=?",
                               d_change, match["defender"])
            else:
                a_change = match["wager_win"] + match["streak_bonus"]
                d_change = -(match["wager_win"] // 2)
                self.store.run("UPDATE mp_players SET trophies=trophies+?, wins=wins+1, streak=streak+1 "
                               "WHERE username=?", a_change, match["attacker"])
                self.store.run("UPDATE mp_players SET trophies=MAX(0, trophies+?) WHERE username=?",
                               d_change, match["defender"])
            self.store.run(
                "UPDATE matches SET finished=?, attacker_won=?, attacker_change=?, defender_change=? WHERE id=?",
                time.time(), 0 if lost else 1, a_change, d_change, match["id"])
            attacker = self.mp_row(match["attacker"])
            self.send_json({"success": True, "data": {"trophies": attacker["trophies"]}})
            return True
        return False

    # records

    def route_record(self, rest):
        me = self.me()
        if not me:
            self.send_json({"success": False}, 403)
            return True
        kind = rest[0] if rest else ""
        if kind == "recent":
            row = self.mp_row(me)
            if row is None:
                return False
            since = row["last_notified"]
            stats = self.store.one(
                "SELECT SUM(CASE WHEN attacker_won=0 THEN 1 ELSE 0 END) AS wins, "
                "SUM(CASE WHEN attacker_won=1 THEN 1 ELSE 0 END) AS losses "
                "FROM matches WHERE defender=? AND finished > ?", me, since)
            self.store.run("UPDATE mp_players SET last_notified=? WHERE username=?", time.time(), me)
            self.send_json({"success": True, "data": {
                "wins": stats["wins"] or 0, "losses": stats["losses"] or 0, "rank": self.rank_of(row)}})
            return True
        if kind in ("attack", "defense"):
            if kind == "attack":
                rows = self.store.all(
                    "SELECT m.*, p.name AS opp_name, p.icon AS opp_icon FROM matches m "
                    "JOIN mp_players p ON p.username = m.defender "
                    "WHERE m.attacker=? AND m.finished IS NOT NULL ORDER BY m.finished DESC LIMIT 20", me)
                data = [{"name": r["opp_name"], "icon": r["opp_icon"], "outcome": r["attacker_change"],
                         "won": bool(r["attacker_won"]), "date": iso(r["finished"])} for r in rows]
            else:
                rows = self.store.all(
                    "SELECT m.*, p.name AS opp_name, p.icon AS opp_icon FROM matches m "
                    "JOIN mp_players p ON p.username = m.attacker "
                    "WHERE m.defender=? AND m.finished IS NOT NULL ORDER BY m.finished DESC LIMIT 20", me)
                data = [{"name": r["opp_name"], "icon": r["opp_icon"], "outcome": r["defender_change"],
                         "won": not r["attacker_won"], "date": iso(r["finished"])} for r in rows]
            self.send_json({"success": True, "data": data})
            return True
        return False

    def player_record(self, username):
        rows = self.store.all(
            "SELECT m.*, a.name AS a_name, a.icon AS a_icon, d.name AS d_name, d.icon AS d_icon "
            "FROM matches m JOIN mp_players a ON a.username = m.attacker "
            "JOIN mp_players d ON d.username = m.defender "
            "WHERE (m.attacker=? OR m.defender=?) AND m.finished IS NOT NULL "
            "ORDER BY m.finished DESC LIMIT 20", username, username)
        data = [{"defender_name": r["d_name"], "defender_icon": r["d_icon"],
                 "outcome": r["attacker_change"] if r["attacker"] == username else r["defender_change"],
                 "attacker_name": r["a_name"], "attacker_icon": r["a_icon"],
                 "attacker_won": bool(r["attacker_won"]), "date": iso(r["finished"])} for r in rows]
        self.send_json({"success": True, "data": data})
        return True

    # leaderboards

    def route_leaderboard(self, rest):
        if not rest:
            rows = self.store.all("SELECT * FROM mp_players ORDER BY trophies DESC, created ASC LIMIT 100")
            self.send_json({"success": True,
                            "data": [self.leaderboard_entry(r, i + 1) for i, r in enumerate(rows)]})
            return True
        if rest[0] in ("rank", "globalrank"):
            row = self.mp_row(self.query.get("username", ""))
            if row is None:
                return False
            self.send_json({"success": True, "data": {"rank": self.rank_of(row)}})
            return True
        row = self.mp_row(unquote_plus(rest[0]))
        if row is None:
            return False
        rank = self.rank_of(row)
        start = max(0, rank - 6)
        rows = self.store.all("SELECT * FROM mp_players ORDER BY trophies DESC, created ASC LIMIT 11 OFFSET ?", start)
        self.send_json({"success": True,
                        "data": [self.leaderboard_entry(r, start + i + 1) for i, r in enumerate(rows)]})
        return True

    # tournaments (weekly, ending Monday 00:00 UTC)

    def settle_tournaments(self):
        tid, _ = current_tournament()
        row = self.store.one("SELECT value FROM meta WHERE key='settled_tournament'")
        settled = int(row["value"]) if row else tid - 1
        if settled >= tid - 1:
            if row is None:
                self.store.run("INSERT OR REPLACE INTO meta (key, value) VALUES ('settled_tournament', ?)", str(settled))
            return
        with self.store.lock:
            players = self.store.all(
                "SELECT username FROM mp_players WHERE trophies > 0 ORDER BY trophies DESC, created ASC")
            for rank, p in enumerate(players, 1):
                self.store.run("INSERT OR IGNORE INTO rewards (username, tournament_id, rank) VALUES (?, ?, ?)",
                               p["username"], tid - 1, rank)
            for rank, p in enumerate(
                    self.store.all("SELECT username FROM mp_players ORDER BY trophies DESC, created ASC"), 1):
                self.store.run("UPDATE mp_players SET prev_rank=? WHERE username=?", rank, p["username"])
            self.store.run("INSERT OR REPLACE INTO meta (key, value) VALUES ('settled_tournament', ?)", str(tid - 1))
        log.info("settled tournament %d (%d ranked players)", tid - 1, len(players))

    def route_tournament(self, method, rest):
        action = rest[0] if rest else ""
        if action == "expiration":
            tid, end = current_tournament()
            self.send_json({"success": True, "data": {
                "tournament_id": tid, "time": end.strftime("%Y-%m-%dT%H:%M:%SZ")}})
            return True
        if action == "player":
            username = self.query.get("username", "")
            rows = self.store.all(
                "SELECT tournament_id, rank FROM rewards WHERE username=? AND redeemed=0", username)
            if not rows:
                return False  # 404 = nothing to collect
            self.send_json({"success": True, "data": [
                {"tournament_id": r["tournament_id"], "outcome": r["rank"]} for r in rows]})
            return True
        if action == "complete":
            username = self.form.get("username", "")
            if not self.claim(username):
                self.send_json({"success": False}, 403)
                return True
            self.store.run("UPDATE rewards SET redeemed=1 WHERE username=? AND tournament_id=?",
                           username, to_int(self.form.get("tournament_id"), -1))
            self.send_json({"success": True})
            return True
        return False


def to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value, low, high):
    return max(low, min(high, value))


def main():
    parser = argparse.ArgumentParser(description="Card Wars community server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("CARDWARS_PORT", 80)))
    parser.add_argument("--db", default=os.environ.get("CARDWARS_DB", "cardwars.db"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    store = Store(args.db)
    httpd = CardWarsServer((args.host, args.port), store)
    log.info("Card Wars server listening on %s:%d (db: %s)", args.host, args.port, os.path.abspath(args.db))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
