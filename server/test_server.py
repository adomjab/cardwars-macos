#!/usr/bin/env python3
"""End-to-end test: starts the server on a free port and replays the requests
the Card Wars client makes, in the same shapes (see cardwars_server.py)."""

import base64
import gzip
import hashlib
import http.cookiejar
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Client:
    """One game install: Unity WWW (no cookies) for the login screen, and a
    cookie-keeping WebClient for everything else, like the real game."""

    def __init__(self, base, udid):
        self.base = base  # ends with "/", like server_settings.json
        self.udid = udid
        self.jar = http.cookiejar.CookieJar()
        self.web = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.www = urllib.request.build_opener()

    def _do(self, opener, req):
        try:
            with opener.open(req, timeout=10) as r:
                return r.status, r.read(), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers

    # Unity WWW (AuthScreenController / SocialManager): no URL escaping
    def www_get(self, path):
        return self._do(self.www, urllib.request.Request(self.base + path))

    # TFServer.GetToJSON / PostToJSON
    def get_json(self, path):
        status, body, _ = self._do(self.web, urllib.request.Request(self.base + path))
        return status, (json.loads(body) if body else None)

    def post_form(self, path, fields):
        data = "&".join("%s=%s" % (k, urllib.parse.quote(str(v), safe="")) for k, v in fields.items())
        req = urllib.request.Request(self.base + path, data=data.encode(), method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        return self._do(self.web, req)

    # SQWebFileServer: "{0}/{1}" with SERVER_URL ending in "/" -> double slash
    def persist_url(self, rest):
        return "%s/persist/%s" % (self.base, rest)

    def get_file(self, rest):
        status, body, headers = self._do(self.web, urllib.request.Request(self.persist_url(rest)))
        text = gzip.decompress(body).decode() if status == 200 else None
        return status, text, headers

    def put_game(self, user, game):
        prefix = "username=%s&score=%d&" % (game.get("PlayerName", ""), game.get("GP", 0))
        payload = prefix + "data=" + base64.b64encode(gzip.compress(json.dumps(game).encode())).decode()
        req = urllib.request.Request(self.persist_url("%s/game" % user), data=payload.encode(), method="PUT",
                                     headers={"Content-Type": "application/octet-stream", "X-UDID": self.udid})
        return self._do(self.web, req)


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        # A carnival starting in 12 hours and a holiday that already started.
        soon = time.gmtime(time.time() + 12 * 3600)
        with open(os.path.join(cls.tmp, "db_GachaSchedule.json"), "w") as f:
            json.dump([
                {"StartDate": "default", "EndDate": "default", "Party": ""},
                {"StartDate": time.strftime("%Y-%m-%d %H:%M +0:00", soon), "EndDate": "2099-01-01 0:00 +0:00",
                 "Party": "party_halloween"},
                {"StartDate": "2001-01-01 0:00 +0:00", "EndDate": "2001-01-02 0:00 +0:00", "Party": "party_gold"},
            ], f)
        with open(os.path.join(cls.tmp, "db_Schedule.json"), "w") as f:
            json.dump([{"item": "Christmas", "category": "battle_level", "startDate": "01/12/2001",
                        "endDate": "31/12/2001"}], f)
        with open(os.path.join(cls.tmp, "announcements.json"), "w") as f:
            json.dump([
                {"id": "welcome", "message": "Welcome to our server!", "coins": 1000, "gems": 5},
                {"id": "old", "message": "Expired", "start": "2001-01-01", "end": "2001-02-01"},
            ], f)
        cls.port = free_port()
        cls.proc = subprocess.Popen(
            [sys.executable, os.path.join(HERE, "cardwars_server.py"), "--host", "127.0.0.1",
             "--port", str(cls.port), "--db", os.path.join(cls.tmp, "test.db"), "--events-url", ""],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", cls.port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        cls.base = "http://127.0.0.1:%d/" % cls.port

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait()

    def login(self, user, password, udid):
        c = Client(self.base, udid)
        status, body, _ = c.www_get("account/exists?user=" + user)
        if body == b"false":
            status, body, _ = c.www_get("account/create?user=%s&pass=%s" % (user, password))
            self.assertTrue(json.loads(body)["success"], body)
        status, body, _ = c.www_get("account/auth?user=%s&pass=%s" % (user, password))
        self.assertTrue(json.loads(body)["success"], body)
        # Session.Authorizing: preAuth then gcAuth must look like a network error
        status, data = c.get_json("account/preAuth/")
        self.assertEqual(status, 200)
        self.assertIn("nonce", data["data"])
        status, body, _ = c.post_form("account/gcAuth/", {"player_id": "guid", "alias": "guid"})
        self.assertEqual(json.loads(body)["error"], "Network error")
        # SessionManager then checks the cloud save, which ties the session
        # cookie to this account.
        self.last_save_status = c.get_file("%s/game" % user)[0]
        return c

    def test_root_and_basics(self):
        c = Client(self.base, "dev")
        status, body, _ = c.www_get("")
        self.assertEqual(status, 200)
        status, text, _ = c.get_file("version.txt")
        self.assertEqual(text, "1.0.0")
        status, text, _ = c.get_file("messages_received_ids")
        self.assertEqual(json.loads(text), [])
        status, data = c.get_json("time/")
        self.assertIn("server_time", data["data"])
        status, _, _ = c.www_get("static/manifest.json")
        self.assertEqual(status, 404)

    def test_accounts(self):
        c = Client(self.base, "dev")
        self.assertEqual(c.www_get("account/exists?user=alice")[1], b"false")
        bad = json.loads(c.www_get("account/create?user=a%20b&pass=xxxx")[1])
        self.assertFalse(bad["success"])
        self.assertIn("message", bad)
        ok = json.loads(c.www_get("account/create?user=alice&pass=secret1")[1])
        self.assertTrue(ok["success"])
        self.assertEqual(c.www_get("account/exists?user=alice")[1], b"true")
        dup = json.loads(c.www_get("account/create?user=alice&pass=other")[1])
        self.assertFalse(dup["success"])
        wrong = json.loads(c.www_get("account/auth?user=alice&pass=nope")[1])
        self.assertFalse(wrong["success"])
        self.assertIn("message", wrong)

    def test_saves(self):
        c = self.login("bob", "pw1234", "device-bob")
        self.assertEqual(self.last_save_status, 404)  # new account: client keeps local save
        game = {"PlayerName": "bob-guid", "GP": 12, "coins": 500}
        status, body, headers = c.put_game("bob", game)
        self.assertEqual(status, 200, body)
        etag = headers["ETag"]
        self.assertTrue(etag.endswith("-" + hashlib.md5(b"device-bob").hexdigest()))
        status, text, headers = c.get_file("bob/game")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(text), game)
        self.assertEqual(headers["ETag"], etag)

        # Someone else (different session, never logged in as bob) can't overwrite it
        other = self.login("mallory", "pw1234", "device-m")
        status, _, _ = other.put_game("bob", {"PlayerName": "x"})
        self.assertEqual(status, 403)

    def test_multiplayer(self):
        a = self.login("carol", "pw1234", "dev-c")
        b = self.login("dave", "pw1234", "dev-d")
        deck_c = base64.b64encode(b"deck-of-carol").decode()
        deck_d = base64.b64encode(b"deck-of-dave").decode()
        for client, user, name, deck in ((a, "carol", "Carol", deck_c), (b, "dave", "Dave", deck_d)):
            status, _ = client.get_json("multiplayer/player/" + user)
            self.assertEqual(status, 404)  # -> game asks for a name
            status, body, _ = client.post_form("multiplayer/new_player/", {
                "name": name, "icon": "icon", "deck": deck, "deck_rank": 10.5, "landscapes": "Corn,Corn",
                "leader": "Finn", "leader_level": 3, "level": 3, "version": 0, "signature": "x"})
            data = json.loads(body)
            self.assertTrue(data["success"], body)
            self.assertEqual(data["data"]["name"], name)

        # name clash -> 403 (ResponseFlag.Invalid)
        e = self.login("erin", "pw1234", "dev-e")
        e.get_json("multiplayer/player/erin")
        status, _, _ = e.post_form("multiplayer/new_player/", {"name": "carol", "deck": "x"})
        self.assertEqual(status, 403)

        status, data = a.get_json("multiplayer/player/carol")
        self.assertEqual(data["trophies"], 0)
        status, body, _ = a.post_form("multiplayer/update_deck/", {
            "name": "carol", "deck": deck_c, "deck_rank": 11, "landscapes": "Corn", "leader": "Finn",
            "leader_level": 4, "version": 0})
        self.assertTrue(json.loads(body)["success"])

        status, body, _ = a.post_form("multiplayer/matchmake/find/", {"name": "carol", "level": 4, "version": 0})
        self.assertEqual(status, 200, body)
        match = json.loads(body)
        for key in ("match_id", "name", "icon", "landscapes", "leader", "expiration_date"):
            self.assertIn(key, match)
        self.assertEqual(match["name"], "Dave")

        status, body, _ = a.post_form("multiplayer/matchmake/start/", {
            "match_id": match["match_id"], "deck_rank": 11, "leader": "Finn", "leader_level": 4})
        self.assertEqual(base64.b64decode(body), b"deck-of-dave")

        status, body, _ = a.post_form("multiplayer/matchmake/complete/", {
            "match_id": match["match_id"], "name": "carol", "loss": "False"})
        result = json.loads(body)
        self.assertTrue(result["success"])
        self.assertGreater(int(result["data"]["trophies"]), 0)

        # Records, notifications, leaderboards, ranks
        status, data = a.get_json("multiplayer/record/attack")
        self.assertTrue(data["data"][0]["won"])
        status, body, _ = b.post_form("multiplayer/record/recent/", {})
        self.assertEqual(json.loads(body)["data"]["losses"], 1)
        status, data = a.get_json("multiplayer/player_record/carol")
        self.assertEqual(data["data"][0]["attacker_name"], "Carol")
        status, data = a.get_json("multiplayer/active_leaderboard/")
        self.assertEqual(data["data"][0]["player_name"], "Carol")
        status, data = a.get_json("multiplayer/active_leaderboard/carol")
        self.assertTrue(data["success"])
        status, data = a.get_json("multiplayer/active_leaderboard/rank/?username=carol")
        self.assertEqual(data["data"]["rank"], 1)
        status, data = a.get_json("multiplayer/tournament/expiration/")
        self.assertIn("time", data["data"])
        status, _ = a.get_json("multiplayer/tournament/player/?username=carol")
        self.assertEqual(status, 404)  # nothing to collect yet

        # Only the attacker can finish a match
        status, body, _ = b.post_form("multiplayer/matchmake/find/", {"name": "carol", "level": 1})
        self.assertEqual(status, 403)


class SoloTest(ServerTest):
    """A server with just one player (its own database)."""

    test_multiplayer = None  # adds other players

    def test_practice_and_tournament(self):
        a = self.login("solo", "pw1234", "dev-solo")
        a.get_json("multiplayer/player/solo")
        deck = base64.b64encode(b"deck-of-solo").decode()
        status, body, _ = a.post_form("multiplayer/new_player/", {
            "name": "Solo", "icon": "icon", "deck": deck, "deck_rank": 10, "landscapes": "Corn",
            "leader": "Finn", "leader_level": 1, "level": 1, "version": 0, "signature": "x"})
        self.assertTrue(json.loads(body)["success"], body)

        # Nobody else: practice against your own deck
        status, body, _ = a.post_form("multiplayer/matchmake/find/", {"name": "solo", "level": 1, "version": 0})
        self.assertEqual(status, 200, body)
        match = json.loads(body)
        self.assertEqual(match["name"], "Solo")
        status, body, _ = a.post_form("multiplayer/matchmake/start/", {"match_id": match["match_id"]})
        self.assertEqual(base64.b64decode(body), b"deck-of-solo")
        status, body, _ = a.post_form("multiplayer/matchmake/complete/", {
            "match_id": match["match_id"], "name": "solo", "loss": "False"})
        self.assertEqual(int(json.loads(body)["data"]["trophies"]), match["wager_win"])
        status, data = a.get_json("multiplayer/record/defense")
        self.assertEqual(data["data"], [])  # practice isn't a defense

        # Tournament ids are ones the game knows (db_Tournament.json: 1-216)
        status, data = a.get_json("multiplayer/tournament/expiration/")
        self.assertTrue(1 <= data["data"]["tournament_id"] <= 216, data)

        # A reward from week 352 is offered and collected as tournament 353 % 216
        db = sqlite3.connect(os.path.join(self.tmp, "test.db"))
        db.execute("INSERT INTO rewards (username, tournament_id, rank) VALUES ('solo', 352, 1)")
        db.commit()
        status, data = a.get_json("multiplayer/tournament/player/?username=solo")
        self.assertEqual(data["data"], [{"tournament_id": 352 % 216 + 1, "outcome": 1}])
        status, body, _ = a.post_form("multiplayer/tournament/complete/", {
            "username": "solo", "tournament_id": 352 % 216 + 1})
        self.assertTrue(json.loads(body)["success"])
        status, _ = a.get_json("multiplayer/tournament/player/?username=solo")
        self.assertEqual(status, 404)
        db.close()


class MessagesTest(ServerTest):
    def test_messages(self):
        c = self.login("frank", "pw1234", "dev-f")
        status, text, _ = c.get_file("messages_received_ids")
        ids = json.loads(text)
        self.assertEqual(sorted(ids), ["carnival-halloween-" + time.strftime("%Y%m%d", time.gmtime(time.time() + 12 * 3600)),
                                       "custom-welcome"])
        for msg_id in ids:
            status, text, _ = c.get_file("messages_get/" + msg_id)
            self.assertEqual(status, 200)
            msg = json.loads(text)
            self.assertIn("message", msg)
            if msg_id == "custom-welcome":
                self.assertEqual((msg["soft_currency"], msg["hard_currency"]), (1000, 5))
            else:
                self.assertIn("Halloween Festival", msg["message"])
        # Shown once: nothing left next time
        self.assertEqual(json.loads(c.get_file("messages_received_ids")[1]), [])
        # Unknown id still answers 200 (the client would hang otherwise)
        status, text, _ = c.get_file("messages_get/nope")
        self.assertEqual(status, 200)
        self.assertIn("message", json.loads(text))

    def test_guest_gets_no_messages(self):
        g = Client(self.base, "guest-dev")
        self.assertEqual(json.loads(g.get_file("messages_received_ids")[1]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
