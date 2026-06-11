#!/usr/bin/env python3
import json
import os

WORKOUTS_DIR = "workouts"
README_PATH = "README.md"


def load_workouts():
    entries = []
    for fname in sorted(os.listdir(WORKOUTS_DIR), reverse=True):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(WORKOUTS_DIR, fname)) as f:
            data = json.load(f)
        entries.append(data)
    return entries[:10]


def build_exercise_table(exercises):
    rows = ["| Exercise | Weight | Sets × Reps | Note |",
            "|----------|--------|-------------|------|"]
    for e in exercises:
        name = e.get("name", "-")
        weight = f"{e['weight_lbs']} lbs" if e.get("weight_lbs") else "-"
        sets = e.get("sets", "-")
        reps = e.get("reps", "-")
        note = e.get("note", "")
        rows.append(f"| {name} | {weight} | {sets}×{reps} | {note} |")
    return "\n".join(rows)


def build_section(entry):
    date = entry.get("date", "-")
    day = entry.get("day", "-")
    workout_type = entry.get("type", "-")
    exercises = [e for e in entry.get("exercises", []) if e.get("completed")]

    table = build_exercise_table(exercises)
    return (
        f"<details>\n"
        f"<summary>{date} · {day} · <b>{workout_type}</b></summary>\n\n"
        f"{table}\n\n"
        f"</details>\n"
    )


def update_readme(entries):
    sections = "\n".join(build_section(e) for e in entries)
    content = f"# Gym Recording\n\n## Latest Workouts\n\n{sections}"
    with open(README_PATH, "w") as f:
        f.write(content)
    print("README updated.")


if __name__ == "__main__":
    entries = load_workouts()
    update_readme(entries)
