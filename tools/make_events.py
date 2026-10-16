#!/usr/bin/env python3
"""Regenerate the game's event schedules so events repeat every year.

The game ships with fixed-date schedules (Blueprints/db_Schedule.json and
db_GachaSchedule.json) that ended in 2024/early 2025, so no events show up
any more. This rebuilds both files with the same yearly pattern for every
year up to LAST_YEAR:

- db_Schedule.json: Halloween (October) and Christmas (December) battle
  levels and menu themes, and the monthly calendar gifts.
- db_GachaSchedule.json: the special card-pack "carnivals", using the 2024
  calendar (the last complete year) shifted to each later year, with every
  carnival using its own odds (a few original rows mixed them up).

Usage: python3 tools/make_events.py OUTPUT_DIR
Reads the untouched originals from tools/original/.
"""

import datetime
import json
import os
import re
import sys

FIRST_YEAR = 2023
LAST_YEAR = 2036
GACHA_TEMPLATE_YEAR = 2024

HERE = os.path.dirname(os.path.abspath(__file__))

CALENDAR_MONTHS = [  # (gift calendar name, month)
    ("January", 1), ("February", 2), ("March", 3), ("April", 4), ("May", 5), ("June", 6),
    ("July", 7), ("August", 8), ("September", 9), ("Halloween", 10), ("November", 11), ("Christmas", 12),
]


def d(day, month, year):
    return "%02d/%02d/%04d" % (day, month, year)


def make_schedule():
    rows = []
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        # Rows with empty dates inherit the dates of the row above them.
        rows += [
            {"item": "Halloween", "category": "battle_level", "startDate": d(1, 10, year), "endDate": d(31, 10, year)},
            {"item": "Halloween_Table", "category": "battle_table", "startDate": "", "endDate": ""},
            {"item": "Halloween_Chair", "category": "battle_chair", "startDate": "", "endDate": ""},
            {"item": "AdventureTimeEnvironmentHalloween", "category": "menu_environment",
             "startDate": d(1, 10, year), "endDate": d(31, 10, year)},
            {"item": "Christmas", "category": "battle_level", "startDate": d(1, 12, year), "endDate": d(31, 12, year)},
            {"item": "Christmas_Table", "category": "battle_table", "startDate": "", "endDate": ""},
            {"item": "Christmas_Chair", "category": "battle_chair", "startDate": "", "endDate": ""},
            {"item": "AdventureTimeEnvironmentChristmas", "category": "menu_environment",
             "startDate": d(1, 12, year), "endDate": d(31, 12, year)},
        ]
        for name, month in CALENDAR_MONTHS:
            end = d(1, month + 1, year) if month < 12 else d(1, 1, year + 1)
            rows.append({"item": name, "category": "calendar_gift", "startDate": d(1, month, year), "endDate": end})
    return rows


def shift_year(date_text, years):
    # "2024-12-26 16:00 -7:00" -> same date `years` later
    return re.sub(r"^(\d{4})", lambda m: str(int(m.group(1)) + years), date_text)


# Each carnival's banner (Party) and the odds it should use (Weight1).
PARTY_WEIGHTS = {
    "party_plains": "PlainsCarnival", "party_leader": "LeaderCarnival", "party_cotton": "CottonCarnival",
    "party_swamp": "SwampCarnival", "party_rare": "RareCarnival", "party_sand": "SandCarnival",
    "party_corn": "CornCarnival", "party_gold": "GoldCarnival", "party_halloween": "HalloweenCarnival",
    "party_obsidian": "ObsidianCarnival", "party_holiday": "HolidayCarnival",
}


def match_odds(row):
    """Some original rows show one carnival's banner but use another's odds
    (e.g. "Rare Card Carnival" with Sandy Beach odds). Use the banner's odds."""
    row = dict(row)
    if row.get("Party") in PARTY_WEIGHTS:
        row["Weight1"] = PARTY_WEIGHTS[row["Party"]]
    return row


# The 2024 calendar ends with an Obsidian Festival from 26 Dec to 29 Jan that
# overlaps the January carnivals; leave that one out (the short late-November
# Obsidian Festival stays).
def is_long_obsidian(row):
    return row.get("Party") == "party_obsidian" and row["StartDate"][5:10] == "12-26" and row["EndDate"][5:10] == "01-29"


def make_gacha():
    with open(os.path.join(HERE, "original", "db_GachaSchedule.json"), encoding="utf-8") as f:
        original = json.load(f)
    defaults = [r for r in original if r["StartDate"].lower() == "default"]
    dated = [r for r in original if r["StartDate"].lower() != "default"]
    template = [r for r in dated if r["StartDate"].startswith(str(GACHA_TEMPLATE_YEAR))]
    dated = [match_odds(r) for r in dated if not is_long_obsidian(r)]
    template = [match_odds(r) for r in template if not is_long_obsidian(r)]
    rows = list(defaults) + dated
    for year in range(GACHA_TEMPLATE_YEAR + 1, LAST_YEAR + 1):
        for r in template:
            row = dict(r)
            row["StartDate"] = shift_year(r["StartDate"], year - GACHA_TEMPLATE_YEAR)
            row["EndDate"] = shift_year(r["EndDate"], year - GACHA_TEMPLATE_YEAR)
            rows.append(row)
    return rows


CARNIVAL_NAMES = {
    "party_plains": ("Plains Party", "Plains cards have 5x chance to drop in the Algebraic Chest."),
    "party_leader": ("Hero Card Carnival", "Hero Cards have 10x chance to drop in the Algebraic Chest."),
    "party_cotton": ("Nicelands Jubilee", "Nicelands cards have 5x chance to drop in the Algebraic Chest."),
    "party_swamp": ("Swamp Shindig", "Swamp cards have 5x chance to drop in the Algebraic Chest."),
    "party_rare": ("Rare Card Carnival", "3x chance for 4 and 5 star cards in the Algebraic Chest."),
    "party_sand": ("Sandy Beach Bash", "Sandy Beach creatures have 5x chance to drop in the Algebraic Chest."),
    "party_corn": ("Corn Carnival", "Corn cards have 5x chance to drop in the Algebraic Chest."),
    "party_gold": ("Gold Gala", "Gold Creatures have 3x chance to drop in the Algebraic Chest."),
    "party_halloween": ("Halloween Festival", "Limited Time Halloween Creatures and Buildings in the Halloween Chest!"),
    "party_obsidian": ("Obsidian Festival", "For a Limited Time, Black Cards are available in the Algebraic Chest."),
    "party_holiday": ("Holiday Festival", "Limited Time Holiday Creatures and Buildings in the Holiday Chest!"),
}
CALENDAR_FROM_YEAR = 2026


def carnival_utc(text):
    """'2026-10-28 16:00 -7:00' -> datetime in UTC (naive)."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2}) (\d{1,2}):(\d{2}) ([+-]?\d{1,2}):(\d{2})$", text)
    y, mo, d, h, mi, oh, om = (int(x) for x in m.groups())
    local = datetime.datetime(y, mo, d, h, mi)
    return local - datetime.timedelta(hours=oh, minutes=-om if oh < 0 else om)


def ics_text(value):
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics_fold(line):
    raw = line.encode("utf-8")
    parts = []
    while len(raw) > 75:
        cut = 75 if not parts else 74
        while (raw[cut] & 0xC0) == 0x80:  # don't split a UTF-8 character
            cut -= 1
        parts.append(raw[:cut])
        raw = raw[cut:]
    parts.append(raw)
    return "\r\n ".join(p.decode("utf-8") for p in parts)


def make_calendar(schedule, gacha):
    """iCalendar file of carnivals and holiday months, each with a reminder
    one day before, for people to subscribe to on their phone or computer."""
    events = []
    for r in gacha:
        if r["StartDate"].lower() == "default" or r.get("Party") not in CARNIVAL_NAMES:
            continue
        start, end = carnival_utc(r["StartDate"]), carnival_utc(r["EndDate"])
        if end.year < CALENDAR_FROM_YEAR:
            continue
        name, desc = CARNIVAL_NAMES[r["Party"]]
        uid = "carnival-%s-%s" % (r["Party"][6:], start.strftime("%Y%m%d"))
        events.append((start, uid, "Card Wars: " + name, desc,
                       "DTSTART:" + start.strftime("%Y%m%dT%H%M%SZ"), "DTEND:" + end.strftime("%Y%m%dT%H%M%SZ")))
    for r in schedule:
        if r["category"] != "battle_level":
            continue
        start = datetime.datetime.strptime(r["startDate"], "%d/%m/%Y")
        end = datetime.datetime.strptime(r["endDate"], "%d/%m/%Y") + datetime.timedelta(days=1)
        if start.year < CALENDAR_FROM_YEAR:
            continue
        uid = "holiday-%s-%s" % (r["item"].lower(), start.strftime("%Y%m%d"))
        events.append((start, uid, "Card Wars: %s month" % r["item"],
                       "%s menu theme and %s battles all month." % (r["item"], r["item"]),
                       "DTSTART;VALUE=DATE:" + start.strftime("%Y%m%d"), "DTEND;VALUE=DATE:" + end.strftime("%Y%m%d")))
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//adomjab//cardwars-macos//EN", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", "X-WR-CALNAME:Card Wars events", "X-PUBLISHED-TTL:P1D",
             "REFRESH-INTERVAL;VALUE=DURATION:P1D"]
    for start, uid, summary, desc, dtstart, dtend in sorted(events):
        lines += ["BEGIN:VEVENT", "UID:%s@cardwars-macos" % uid, "DTSTAMP:20260101T000000Z", dtstart, dtend,
                  "SUMMARY:" + ics_text(summary), "DESCRIPTION:" + ics_text(desc),
                  "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-P1D", "DESCRIPTION:" + ics_text(summary + " starts tomorrow"),
                  "END:VALARM", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(ics_fold(l) for l in lines) + "\r\n", len(events)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    schedule, gacha = make_schedule(), make_gacha()
    for name, rows in (("db_Schedule.json", schedule), ("db_GachaSchedule.json", gacha)):
        with open(os.path.join(out, name), "w", encoding="utf-8", newline="\n") as f:
            json.dump(rows, f, indent="\t")
            f.write("\n")
        print("wrote %s (%d entries)" % (os.path.join(out, name), len(rows)))
    ics, n = make_calendar(schedule, gacha)
    with open(os.path.join(out, "CardWars-events.ics"), "w", encoding="utf-8", newline="") as f:
        f.write(ics)
    print("wrote %s (%d events)" % (os.path.join(out, "CardWars-events.ics"), n))


if __name__ == "__main__":
    main()
