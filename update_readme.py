#!/usr/bin/env python3
import json
import os
from datetime import datetime

WORKOUTS_DIR = "workouts"
README_PATH = "README.md"
HTML_PATH = "index.html"


def load_workouts():
    entries = []
    for fname in sorted(os.listdir(WORKOUTS_DIR), reverse=True):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(WORKOUTS_DIR, fname)) as f:
            data = json.load(f)
        entries.append(data)
    return entries[:10]


def build_exercise_table_md(exercises):
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


def build_section_md(entry):
    date = entry.get("date", "-")
    day = entry.get("day", "-")
    workout_type = entry.get("type", "-")
    exercises = [e for e in entry.get("exercises", []) if e.get("completed")]
    table = build_exercise_table_md(exercises)
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


TYPE_COLORS = {
    "Upper":   "#4f8ef7",
    "Lower":   "#f7934f",
    "Class":   "#a04ff7",
    "Running": "#4ff7a0",
}
TYPE_DEFAULT = "#888"


def build_exercise_rows_html(exercises):
    rows = ""
    for e in exercises:
        name = e.get("name", "-")
        weight = f"{e['weight_lbs']} lbs" if e.get("weight_lbs") else "-"
        sets = e.get("sets", "-")
        reps = e.get("reps", "-")
        note = e.get("note", "")
        rows += (
            f"<tr>"
            f"<td>{name}</td>"
            f"<td>{weight}</td>"
            f"<td>{sets}×{reps}</td>"
            f"<td class='note'>{note}</td>"
            f"</tr>\n"
        )
    return rows


def build_card_html(entry):
    date = entry.get("date", "-")
    day = entry.get("day", "-")
    workout_type = entry.get("type", "-")
    color = TYPE_COLORS.get(workout_type, TYPE_DEFAULT)

    if workout_type == "Class":
        class_name = entry.get("name", "Class")
        duration = entry.get("duration_minutes")
        duration_str = f"{duration} minutes" if duration else ""
        detail = f"""
    <div class="class-detail">
      <span class="class-name">{class_name}</span>
      {"<span class='class-duration'>· " + duration_str + "</span>" if duration_str else ""}
    </div>"""
        summary_right = f'<span class="count">{class_name}</span>'
        return f"""
  <details class="card">
    <summary>
      <span class="date">{date}</span>
      <span class="day">{day}</span>
      <span class="badge" style="background:{color}22;color:{color};border-color:{color}44">{workout_type}</span>
      {summary_right}
    </summary>{detail}
  </details>"""

    exercises = [e for e in entry.get("exercises", []) if e.get("completed")]
    rows = build_exercise_rows_html(exercises)
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
      <thead>
        <tr><th>Exercise</th><th>Weight</th><th>Sets×Reps</th><th>Note</th></tr>
      </thead>
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
      background: #0d1117;
      color: #e6edf3;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      padding: 2rem 1rem;
      min-height: 100vh;
    }}

    .container {{
      max-width: 720px;
      margin: 0 auto;
    }}

    header {{
      margin-bottom: 2rem;
    }}

    header h1 {{
      font-size: 1.6rem;
      font-weight: 700;
      color: #f0f6fc;
    }}

    header p {{
      margin-top: .4rem;
      color: #7d8590;
      font-size: .9rem;
    }}

    .section-title {{
      font-size: .75rem;
      font-weight: 600;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: #7d8590;
      margin-bottom: 1rem;
    }}

    .card {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 10px;
      margin-bottom: .75rem;
      overflow: hidden;
      transition: border-color .15s;
    }}

    .card:hover {{
      border-color: #484f58;
    }}

    .card summary {{
      display: flex;
      align-items: center;
      gap: .75rem;
      padding: .85rem 1.1rem;
      cursor: pointer;
      list-style: none;
      user-select: none;
    }}

    .card summary::-webkit-details-marker {{ display: none; }}

    .card summary::before {{
      content: "›";
      font-size: 1.1rem;
      color: #7d8590;
      transition: transform .2s;
      flex-shrink: 0;
    }}

    .card[open] summary::before {{
      transform: rotate(90deg);
    }}

    .date {{
      font-size: .9rem;
      font-weight: 600;
      color: #e6edf3;
      min-width: 100px;
    }}

    .day {{
      font-size: .85rem;
      color: #7d8590;
      flex: 1;
    }}

    .badge {{
      font-size: .75rem;
      font-weight: 600;
      padding: .2rem .6rem;
      border-radius: 20px;
      border: 1px solid;
    }}

    .count {{
      font-size: .78rem;
      color: #7d8590;
      flex-shrink: 0;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: .875rem;
    }}

    thead tr {{
      background: #0d1117;
    }}

    th {{
      text-align: left;
      padding: .5rem 1.1rem;
      font-size: .72rem;
      font-weight: 600;
      letter-spacing: .05em;
      text-transform: uppercase;
      color: #7d8590;
      border-top: 1px solid #21262d;
    }}

    td {{
      padding: .55rem 1.1rem;
      border-top: 1px solid #21262d;
      color: #c9d1d9;
    }}

    td.note {{
      color: #f7934f;
      font-size: .82rem;
    }}

    tbody tr:hover td {{
      background: #1c2128;
    }}

    .class-detail {{
      padding: .75rem 1.1rem 1rem 2.8rem;
      border-top: 1px solid #21262d;
      display: flex;
      align-items: center;
      gap: .5rem;
    }}

    .class-name {{
      font-size: .95rem;
      font-weight: 600;
      color: #e6edf3;
    }}

    .class-duration {{
      font-size: .85rem;
      color: #7d8590;
    }}

    footer {{
      margin-top: 2.5rem;
      text-align: center;
      font-size: .78rem;
      color: #484f58;
    }}
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
    entries = load_workouts()
    update_readme()
    update_html(entries)
    print("README and index.html updated.")
