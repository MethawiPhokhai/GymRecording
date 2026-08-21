#!/usr/bin/env python3
"""
Workout logger for GymRecording repo.

Usage:
  python scripts/log_workout.py list upper
  python scripts/log_workout.py record upper 2026-08-08 --data "shoulder press:50:3:15" "bench press:25:3:10"
  python scripts/log_workout.py record upper --data "shoulder press:50:3:15"
  python scripts/log_workout.py progress upper
  python scripts/log_workout.py cardio
  python scripts/log_workout.py summary
"""

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"
WORKOUTS_DIR = REPO_ROOT / "workouts"

BANGKOK_TZ = timezone(timedelta(hours=7))
DAY_NAMES_TH = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def load_template(template_name: str) -> dict:
    path = TEMPLATES_DIR / f"{template_name}.json"
    if not path.exists():
        available = sorted(p.stem for p in TEMPLATES_DIR.glob("*.json"))
        raise FileNotFoundError(f"Template '{template_name}' not found. Available: {', '.join(available)}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_template(template_name: str):
    template = load_template(template_name)
    print(f"\n📋 Template: {template['type']}\n")
    for i, ex in enumerate(template["exercises"], 1):
        weight = ex.get("default_weight_lbs")
        sets = ex.get("default_sets")
        reps = ex.get("default_reps")
        weight_str = f"{weight} lbs" if weight is not None else "bodyweight / no weight"
        print(f"  {i}. {ex['name']}")
        print(f"     แนะนำ: {weight_str} × {sets} sets × {reps} reps")
    print()


def parse_exercise_data(data_strings: list[str]) -> list[dict]:
    exercises = []
    for s in data_strings:
        # Format: "name:weight:sets:reps" or "name::sets:reps" for bodyweight/no weight
        parts = s.split(":")
        if len(parts) != 4:
            raise ValueError(f"Invalid format: '{s}'. Use 'name:weight:sets:reps' (weight empty for bodyweight)")
        name, weight_str, sets_str, reps_str = parts
        exercises.append({
            "name": name.strip(),
            "completed": True,
            "weight_lbs": int(weight_str) if weight_str.strip() else None,
            "sets": int(sets_str),
            "reps": int(reps_str),
        })
    return exercises


def record_running(date_str: str | None, duration_minutes: float, distance_km: float,
                   pace: str, avg_hr: int | None, calories: int | None):
    if date_str is None:
        date_obj = datetime.now(BANGKOK_TZ)
    else:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=BANGKOK_TZ)

    day_name = DAY_NAMES_TH[date_obj.weekday()]
    date_str = date_obj.strftime("%Y-%m-%d")

    filename = f"{date_str}-running-web.json"
    filepath = WORKOUTS_DIR / filename

    workout = {
        "date": date_str,
        "day": day_name,
        "type": "Running",
        "duration_minutes": duration_minutes,
        "distance_km": distance_km,
        "pace": pace,
        "avg_heart_rate_bpm": avg_hr,
        "calories": calories,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(workout, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Running log saved to: {filepath.relative_to(REPO_ROOT)}")
    print(json.dumps(workout, indent=2, ensure_ascii=False))
    return filepath


def record_workout(template_name: str, date_str: str | None, data_strings: list[str]):
    template = load_template(template_name)
    template_names = {normalize_name(ex["name"]): ex["name"] for ex in template["exercises"]}
    raw_exercises = parse_exercise_data(data_strings)

    # Normalize exercise names to match template names (case-insensitive)
    exercises = []
    for ex in raw_exercises:
        key = normalize_name(ex["name"])
        if key in template_names:
            ex["name"] = template_names[key]
        exercises.append(ex)

    if date_str is None:
        date_obj = datetime.now(BANGKOK_TZ)
    else:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=BANGKOK_TZ)

    day_name = DAY_NAMES_TH[date_obj.weekday()]
    date_str = date_obj.strftime("%Y-%m-%d")

    # Build filename: e.g. 2026-08-08-upper.json
    filename = f"{date_str}-{template_name}.json"
    filepath = WORKOUTS_DIR / filename

    workout = {
        "date": date_str,
        "day": day_name,
        "type": template["type"],
        "exercises": exercises,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(workout, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Workout saved to: {filepath.relative_to(REPO_ROOT)}")
    print(json.dumps(workout, indent=2, ensure_ascii=False))
    return filepath


def push_to_github():
    print("\n🚀 Pushing to GitHub...")
    try:
        # Detect default branch from remote
        result = subprocess.run(["git", "remote", "show", "origin"],
                                cwd=REPO_ROOT, capture_output=True, text=True, check=True)
        default_branch = "main"
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("HEAD branch:"):
                default_branch = line.split(":", 1)[1].strip()
                break

        # Ensure local branch tracks the remote default branch
        subprocess.run(["git", "checkout", "-B", default_branch, f"origin/{default_branch}"],
                       cwd=REPO_ROOT, check=True)
        subprocess.run(["git", "pull", "origin", default_branch], cwd=REPO_ROOT, check=True)
        subprocess.run(["git", "add", "workouts/"], cwd=REPO_ROOT, check=True)
        status = subprocess.run(["git", "status", "--porcelain", "workouts/"],
                                cwd=REPO_ROOT, capture_output=True, text=True, check=True)
        if not status.stdout.strip():
            print("ℹ️ No workout changes to push.")
            return
        subprocess.run(["git", "commit", "-m", "Add workout log"], cwd=REPO_ROOT, check=True)
        subprocess.run(["git", "push", "origin", default_branch], cwd=REPO_ROOT, check=True)
        print("✅ Pushed to GitHub successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git push failed: {e}", file=sys.stderr)
        raise


def normalize_name(name: str) -> str:
    return name.strip().lower()


def load_all_workouts() -> list[dict]:
    workouts = []
    if not WORKOUTS_DIR.exists():
        return workouts
    for path in sorted(WORKOUTS_DIR.glob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["_source"] = path.name
            # Normalize exercise names
            for ex in data.get("exercises", []):
                ex["_key"] = normalize_name(ex.get("name", ""))
            workouts.append(data)
        except Exception:
            continue
    return sorted(workouts, key=lambda w: w.get("date", ""))


def fmt_weight(w):
    return f"{w} lbs" if w is not None else "bodyweight"


def calc_volume(weight, sets, reps):
    s = sets or 0
    r = reps or 0
    if weight is None:
        return s * r  # bodyweight volume proxy
    return weight * s * r


def progress_summary(template_filter: str | None = None):
    workouts = load_all_workouts()
    if not workouts:
        print("\nยังไม่มีข้อมูล workout ครับ\n")
        return

    # Filter by type if requested
    if template_filter:
        template_filter = template_filter.capitalize()
        workouts = [w for w in workouts if w.get("type", "").lower() == template_filter.lower()]
        if not workouts:
            print(f"\nไม่พบข้อมูลประเภท {template_filter} ครับ\n")
            return

    last = workouts[-1]
    exercises_by_name = defaultdict(list)
    for w in workouts:
        for ex in w.get("exercises", []):
            exercises_by_name[ex["_key"]].append({
                "display_name": ex["name"],
                "date": w["date"],
                "weight_lbs": ex.get("weight_lbs"),
                "sets": ex.get("sets"),
                "reps": ex.get("reps"),
                "volume": calc_volume(ex.get("weight_lbs"), ex.get("sets"), ex.get("reps")),
            })

    print(f"\n📊 LAST SESSION")
    print(f"   {last['date']} · {last['day']} · {last['type']} · {len(last.get('exercises', []))} exercises\n")

    # Progressive overload: compare last session to previous same type
    same_type_prev = [w for w in workouts[:-1] if w.get("type") == last.get("type")]
    if same_type_prev:
        prev = same_type_prev[-1]
        prev_ex_by_key = {ex["_key"]: ex for ex in prev.get("exercises", [])}
        improved = 0
        total = 0
        for ex in last.get("exercises", []):
            key = ex["_key"]
            if key in prev_ex_by_key:
                total += 1
                prev_ex = prev_ex_by_key[key]
                cur_vol = calc_volume(ex.get("weight_lbs"), ex.get("sets"), ex.get("reps"))
                prev_vol = calc_volume(prev_ex.get("weight_lbs"), prev_ex.get("sets"), prev_ex.get("reps"))
                if cur_vol > prev_vol:
                    improved += 1
        print(f"📈 PROGRESSIVE OVERLOAD")
        print(f"   {improved}/{total} exercises improved vs previous {last['type']} session\n")
    else:
        print(f"📈 PROGRESSIVE OVERLOAD")
        print(f"   ไม่มี session ก่อนหน้าของ {last['type']} ให้เปรียบเทียบ\n")

    print(f"🏋️ EXERCISE PROGRESS (latest first)\n")
    for key, history in sorted(exercises_by_name.items(), key=lambda x: -len(x[1])):
        latest = history[-1]
        prev = history[-2] if len(history) >= 2 else None
        line = f"   {latest['display_name']}: {fmt_weight(latest['weight_lbs'])} · {latest['sets']}×{latest['reps']} · {latest['date']}"
        if prev:
            change = latest["volume"] - prev["volume"]
            pct = (change / prev["volume"] * 100) if prev["volume"] else 0
            if change > 0:
                line += f"  ▲ +{pct:.0f}%"
            elif change < 0:
                line += f"  ▼ {pct:.0f}%"
            else:
                line += "  — same"
        print(line)
    print()


def cardio_summary():
    workouts = load_all_workouts()
    runs = [w for w in workouts if w.get("type", "").lower() == "running"]
    if not runs:
        print("\nยังไม่มีข้อมูลการวิ่งครับ\n")
        return

    print(f"\n🏃 CARDIO SUMMARY ({len(runs)} runs)\n")
    latest = runs[-1]
    print(f"   ล่าสุด: {latest['date']} · {latest.get('duration_minutes', '-')} min · "
          f"{latest.get('distance_km', '-')} km · {latest.get('pace', '-')} · "
          f"HR {latest.get('avg_heart_rate_bpm', '-')}\n")

    # Trend: compare latest to previous
    if len(runs) >= 2:
        prev = runs[-2]
        cur_dist = latest.get("distance_km", 0) or 0
        prev_dist = prev.get("distance_km", 0) or 0
        cur_dur = latest.get("duration_minutes", 0) or 0
        prev_dur = prev.get("duration_minutes", 0) or 0
        cur_pace_str = latest.get("pace", "")
        prev_pace_str = prev.get("pace", "")

        def parse_pace(p):
            try:
                return float(p.replace(" min/km", "").strip())
            except Exception:
                return None

        cur_pace = parse_pace(cur_pace_str)
        prev_pace = parse_pace(prev_pace_str)

        print(f"   vs รอบก่อน ({prev['date']}):")
        if cur_dist and prev_dist:
            dist_change = (cur_dist - prev_dist) / prev_dist * 100
            print(f"     📍 Distance: {cur_dist} km vs {prev_dist} km ({'+' if dist_change >= 0 else ''}{dist_change:.1f}%)")
        if cur_dur and prev_dur:
            dur_change = (cur_dur - prev_dur) / prev_dur * 100
            print(f"     ⏱️ Duration: {cur_dur} min vs {prev_dur} min ({'+' if dur_change >= 0 else ''}{dur_change:.1f}%)")
        if cur_pace and prev_pace:
            pace_change = prev_pace - cur_pace  # lower pace = faster
            print(f"     ⚡ Pace: {cur_pace_str} vs {prev_pace_str} ({'+' if pace_change >= 0 else ''}{pace_change:.2f} min/km)")
        print()

    print(f"   ประวัติทั้งหมด:")
    for r in runs[-5:]:  # last 5
        print(f"     {r['date']}: {r.get('duration_minutes', '-')} min, {r.get('distance_km', '-')} km, "
              f"{r.get('pace', '-')}, HR {r.get('avg_heart_rate_bpm', '-')}")
    print()


def full_summary():
    workouts = load_all_workouts()
    if not workouts:
        print("\nยังไม่มีข้อมูล workout ครับ\n")
        return

    print(f"\n📋 WORKOUT SUMMARY\n")
    print(f"   ทั้งหมด {len(workouts)} sessions\n")

    by_type = defaultdict(list)
    for w in workouts:
        by_type[w.get("type", "Unknown")].append(w)

    print(f"   แยกตามประเภท:")
    for t, ws in sorted(by_type.items(), key=lambda x: -len(x[1])):
        print(f"     • {t}: {len(ws)} sessions")
    print()

    last = workouts[-1]
    print(f"   ล่าสุด: {last['date']} · {last['day']} · {last['type']} · {len(last.get('exercises', []))} exercises")
    for ex in last.get("exercises", []):
        print(f"     - {ex['name']}: {fmt_weight(ex.get('weight_lbs'))} · {ex['sets']}×{ex['reps']}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Log workouts to GymRecording repo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List exercises in a template")
    list_parser.add_argument("template", help="Template name (e.g. upper, lower, fullbody)")

    record_parser = subparsers.add_parser("record", help="Record a workout")
    record_parser.add_argument("template", help="Template name (e.g. upper, lower, fullbody)")
    record_parser.add_argument("date", nargs="?", help="Date in YYYY-MM-DD format (default: today)")
    record_parser.add_argument("--data", nargs="+", required=True,
                               help='Exercise data: "name:weight:sets:reps" (weight empty for bodyweight)')
    record_parser.add_argument("--push", action="store_true", help="Push to GitHub after saving")

    run_parser = subparsers.add_parser("running", help="Record a running/cardio session")
    run_parser.add_argument("date", nargs="?", help="Date in YYYY-MM-DD format (default: today)")
    run_parser.add_argument("--duration", type=float, required=True, help="Duration in minutes")
    run_parser.add_argument("--distance", type=float, required=True, help="Distance in km")
    run_parser.add_argument("--pace", required=True, help="Pace e.g. 7:30 min/km")
    run_parser.add_argument("--hr", type=int, help="Average heart rate in bpm")
    run_parser.add_argument("--calories", type=int, help="Calories burned")
    run_parser.add_argument("--push", action="store_true", help="Push to GitHub after saving")

    progress_parser = subparsers.add_parser("progress", help="Show exercise progress summary")
    progress_parser.add_argument("template", nargs="?", help="Filter by template type (upper, lower, etc.)")

    cardio_parser = subparsers.add_parser("cardio", help="Show cardio/running summary")

    summary_parser = subparsers.add_parser("summary", help="Show overall workout summary")

    args = parser.parse_args()

    if args.command == "list":
        list_template(args.template)
    elif args.command == "record":
        record_workout(args.template, args.date, args.data)
        if args.push:
            push_to_github()
    elif args.command == "running":
        record_running(args.date, args.duration, args.distance, args.pace, args.hr, args.calories)
        if args.push:
            push_to_github()
    elif args.command == "progress":
        progress_summary(args.template)
    elif args.command == "cardio":
        cardio_summary()
    elif args.command == "summary":
        full_summary()


if __name__ == "__main__":
    main()
