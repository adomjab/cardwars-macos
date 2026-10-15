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


def make_gacha():
    with open(os.path.join(HERE, "original", "db_GachaSchedule.json"), encoding="utf-8") as f:
        original = json.load(f)
    defaults = [r for r in original if r["StartDate"].lower() == "default"]
    dated = [r for r in original if r["StartDate"].lower() != "default"]
    template = [r for r in dated if r["StartDate"].startswith(str(GACHA_TEMPLATE_YEAR))]
    dated = [match_odds(r) for r in dated]
    template = [match_odds(r) for r in template]
    rows = list(defaults) + dated
    for year in range(GACHA_TEMPLATE_YEAR + 1, LAST_YEAR + 1):
        for r in template:
            row = dict(r)
            row["StartDate"] = shift_year(r["StartDate"], year - GACHA_TEMPLATE_YEAR)
            row["EndDate"] = shift_year(r["EndDate"], year - GACHA_TEMPLATE_YEAR)
            rows.append(row)
    return rows


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    for name, rows in (("db_Schedule.json", make_schedule()), ("db_GachaSchedule.json", make_gacha())):
        with open(os.path.join(out, name), "w", encoding="utf-8", newline="\n") as f:
            json.dump(rows, f, indent="\t")
            f.write("\n")
        print("wrote %s (%d entries)" % (os.path.join(out, name), len(rows)))


if __name__ == "__main__":
    main()
