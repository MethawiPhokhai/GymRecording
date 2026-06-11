#!/usr/bin/env python3
import json
import os
from datetime import datetime

WORKOUTS_DIR = "workouts"
README_PATH = "README.md"
DAYS_TH = {
    "Monday": "Monday",
    "Tuesday": "Tuesday",
    "Wednesday": "Wednesday",
    "Thursday": "Thursday",
    "Friday": "Friday",
    "Saturday": "Saturday",
    "Sunday": "Sunday",
}

def load_workouts():
    entries = []
    for fname in sorted(os.listdir(WORKOUTS_DIR), reverse=True):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(WORKOUTS_DIR, fname)) as f:
            data = json.load(f)
        entries.append(data)
    return entries[:10]

def build_table(entries):
    lines = [
        "| Date | Day | Type |",
        "|------|-----|------|",
    ]
    for e in entries:
        date = e.get("date", "-")
        day = e.get("day", "-")
        workout_type = e.get("type", "-")
        lines.append(f"| {date} | {day} | {workout_type} |")
    return "\n".join(lines)

def update_readme(table):
    header = "# Gym Recording\n\n## Latest Workouts\n\n"
    with open(README_PATH, "w") as f:
        f.write(header + table + "\n")

if __name__ == "__main__":
    entries = load_workouts()
    table = build_table(entries)
    update_readme(table)
    print("README updated.")
