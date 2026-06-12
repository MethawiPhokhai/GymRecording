#!/usr/bin/env python3
import json
import os
from datetime import datetime

WORKOUTS_DIR = "workouts"
TEMPLATES_DIR = "templates"
README_PATH = "README.md"
HTML_PATH = "index.html"


def load_templates():
    templates = {}
    for fname in os.listdir(TEMPLATES_DIR):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(TEMPLATES_DIR, fname)) as f:
            data = json.load(f)
        templates[data["type"]] = data
    return templates


def load_workouts():
    entries = []
    for fname in sorted(os.listdir(WORKOUTS_DIR), reverse=True):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(WORKOUTS_DIR, fname)) as f:
            data = json.load(f)
        entries.append(data)
    return entries[:10]


def merge_exercises(session_exercises, template):
    if not template:
        return session_exercises
    pool = {e["name"]: e for e in template.get("exercises", [])}
    merged = []
    for ex in session_exercises:
        name = ex["name"]
        base = pool.get(name, {})
        merged.append({
            "name": name,
            "weight_lbs": ex.get("weight_lbs") or base.get("default_weight_lbs"),
            "sets":       ex.get("sets")       or base.get("default_sets"),
            "reps":       ex.get("reps")       or base.get("default_reps"),
            "completed":  ex.get("completed", False),
            "note":       ex.get("note", ""),
        })
    return merged


def resolve_session(entry, templates):
    workout_type = entry.get("type", "")
    template = templates.get(workout_type)

    if workout_type == "Class":
        class_name = entry.get("name", "")
        duration = entry.get("duration_minutes")
        if not duration and template:
            pool = {c["name"]: c for c in template.get("classes", [])}
            duration = pool.get(class_name, {}).get("default_duration_minutes")
        return {**entry, "duration_minutes": duration}

    if workout_type == "Running":
        return entry

    exercises = [e for e in entry.get("exercises", []) if e.get("completed")]
    merged = merge_exercises(exercises, template)
    return {**entry, "exercises": merged}


# ── Markdown ────────────────────────────────────────────────────────────────

def build_section_md(entry):
    date = entry.get("date", "-")
    day = entry.get("day", "-")
    workout_type = entry.get("type", "-")

    if workout_type == "Class":
        class_name = entry.get("name", "Class")
        duration = entry.get("duration_minutes", "")
        body = f"{class_name} · {duration} minutes" if duration else class_name
        return (
            f"<details>\n"
            f"<summary>{date} · {day} · <b>{workout_type}</b></summary>\n\n"
            f"{body}\n\n"
            f"</details>\n"
        )

    exercises = entry.get("exercises", [])
    rows = ["| Exercise | Weight | Sets × Reps | Note |",
            "|----------|--------|-------------|------|"]
    for e in exercises:
        weight = f"{e['weight_lbs']} lbs" if e.get("weight_lbs") else "-"
        rows.append(f"| {e['name']} | {weight} | {e['sets']}×{e['reps']} | {e.get('note','')} |")
    table = "\n".join(rows)
    return (
        f"<details>\n"
        f"<summary>{date} · {day} · <b>{workout_type}</b></summary>\n\n"
        f"{table}\n\n"
        f"</details>\n"
    )


def update_readme():
    content = (
        "# Gym Recording\n\n"
        "Personal workout log — tracking sets, reps, and weights over time.\n\n"
        "> View the full log → [**gymrecording page**](https://methawiphokhai.github.io/GymRecording/)\n"
    )
    with open(README_PATH, "w") as f:
        f.write(content)


# ── HTML ─────────────────────────────────────────────────────────────────────

TYPE_COLORS = {
    "Upper":   "#4f8ef7",
    "Lower":   "#f7934f",
    "Class":   "#a04ff7",
    "Running": "#4ff7a0",
}
TYPE_DEFAULT = "#888"


def build_card_html(entry):
    date = entry.get("date", "-")
    day = entry.get("day", "-")
    workout_type = entry.get("type", "-")
    color = TYPE_COLORS.get(workout_type, TYPE_DEFAULT)

    if workout_type == "Running":
        duration = entry.get("duration_minutes", "-")
        distance = entry.get("distance_km")
        note = entry.get("note", "")
        parts = []
        if duration: parts.append(f"{duration} min")
        if distance: parts.append(f"{distance} km")
        if note:     parts.append(note)
        detail_str = " · ".join(parts)
        return f"""
  <details class="card">
    <summary>
      <span class="date">{date}</span>
      <span class="day">{day}</span>
      <span class="badge" style="background:{color}22;color:{color};border-color:{color}44">{workout_type}</span>
      <span class="count">{detail_str}</span>
    </summary>
    <div class="class-detail">
      <span class="class-name">{detail_str}</span>
    </div>
  </details>"""

    if workout_type == "Class":
        class_name = entry.get("name", "Class")
        duration = entry.get("duration_minutes")
        duration_str = f"· {duration} minutes" if duration else ""
        return f"""
  <details class="card">
    <summary>
      <span class="date">{date}</span>
      <span class="day">{day}</span>
      <span class="badge" style="background:{color}22;color:{color};border-color:{color}44">{workout_type}</span>
      <span class="count">{class_name}</span>
    </summary>
    <div class="class-detail">
      <span class="class-name">{class_name}</span>
      {"<span class='class-duration'>" + duration_str + "</span>" if duration_str else ""}
    </div>
  </details>"""

    exercises = entry.get("exercises", [])
    rows = ""
    for e in exercises:
        weight = f"{e['weight_lbs']} lbs" if e.get("weight_lbs") else "-"
        rows += (
            f"<tr>"
            f"<td>{e['name']}</td>"
            f"<td>{weight}</td>"
            f"<td>{e['sets']}×{e['reps']}</td>"
            f"<td class='note'>{e.get('note','')}</td>"
            f"</tr>\n"
        )
    count = len(exercises)
    return f"""
  <details class="card">
    <summary>
      <span class="date">{date}</span>
      <span class="day">{day}</span>
      <span class="badge" style="background:{color}22;color:{color};border-color:{color}44">{workout_type}</span>
      <span class="count">{count} exercises</span>
    </summary>
    <table>
      <thead><tr><th>Exercise</th><th>Weight</th><th>Sets×Reps</th><th>Note</th></tr></thead>
      <tbody>
{rows}      </tbody>
    </table>
  </details>"""


def update_html(entries):
    cards = "\n".join(build_card_html(e) for e in entries)
    updated = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Gym Recording</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0d1117; color: #e6edf3;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      padding: 2rem 1rem; min-height: 100vh;
    }}
    .container {{ max-width: 720px; margin: 0 auto; }}
    header {{ margin-bottom: 2rem; }}
    header h1 {{ font-size: 1.6rem; font-weight: 700; color: #f0f6fc; }}
    header p {{ margin-top: .4rem; color: #7d8590; font-size: .9rem; }}
    .section-title {{
      font-size: .75rem; font-weight: 600; letter-spacing: .08em;
      text-transform: uppercase; color: #7d8590; margin-bottom: 1rem;
    }}
    .card {{
      background: #161b22; border: 1px solid #30363d;
      border-radius: 10px; margin-bottom: .75rem;
      overflow: hidden; transition: border-color .15s;
    }}
    .card:hover {{ border-color: #484f58; }}
    .card summary {{
      display: flex; align-items: center; gap: .75rem;
      padding: .85rem 1.1rem; cursor: pointer;
      list-style: none; user-select: none;
    }}
    .card summary::-webkit-details-marker {{ display: none; }}
    .card summary::before {{
      content: "›"; font-size: 1.1rem; color: #7d8590;
      transition: transform .2s; flex-shrink: 0;
    }}
    .card[open] summary::before {{ transform: rotate(90deg); }}
    .date {{ font-size: .9rem; font-weight: 600; color: #e6edf3; min-width: 100px; }}
    .day {{ font-size: .85rem; color: #7d8590; flex: 1; }}
    .badge {{
      font-size: .75rem; font-weight: 600;
      padding: .2rem .6rem; border-radius: 20px; border: 1px solid;
    }}
    .count {{ font-size: .78rem; color: #7d8590; flex-shrink: 0; }}
    table {{ width: 100%; border-collapse: collapse; font-size: .875rem; }}
    thead tr {{ background: #0d1117; }}
    th {{
      text-align: left; padding: .5rem 1.1rem;
      font-size: .72rem; font-weight: 600; letter-spacing: .05em;
      text-transform: uppercase; color: #7d8590; border-top: 1px solid #21262d;
    }}
    td {{ padding: .55rem 1.1rem; border-top: 1px solid #21262d; color: #c9d1d9; }}
    td.note {{ color: #f7934f; font-size: .82rem; }}
    tbody tr:hover td {{ background: #1c2128; }}
    .class-detail {{
      padding: .75rem 1.1rem 1rem 2.8rem;
      border-top: 1px solid #21262d;
      display: flex; align-items: center; gap: .5rem;
    }}
    .class-name {{ font-size: .95rem; font-weight: 600; color: #e6edf3; }}
    .class-duration {{ font-size: .85rem; color: #7d8590; }}
    footer {{ margin-top: 2.5rem; text-align: center; font-size: .78rem; color: #484f58; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Gym Recording</h1>
      <p>Personal workout log — tracking sets, reps, and weights over time.</p>
    </header>
    <p class="section-title">Latest 10 Workouts</p>
    {cards}
    <footer>Updated {updated}</footer>
  </div>
</body>
</html>
"""
    with open(HTML_PATH, "w") as f:
        f.write(html)


if __name__ == "__main__":
    templates = load_templates()
    entries = load_workouts()
    resolved = [resolve_session(e, templates) for e in entries]
    update_readme()
    update_html(resolved)
    print("README and index.html updated.")
