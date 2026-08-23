#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone, timedelta

BKK = timezone(timedelta(hours=7))

WORKOUTS_DIR = "workouts"
TEMPLATES_DIR = "templates"
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
    return entries


def apply_latest_defaults(templates, all_entries):
    """Use the most recently recorded weight of each exercise as its template default."""
    latest = {}
    for entry in sorted(all_entries, key=lambda e: e.get("date", "")):
        for ex in entry.get("exercises", []):
            if ex.get("weight_kg") or ex.get("weight_lbs"):
                latest[ex["name"]] = (ex.get("weight_kg"), ex.get("weight_lbs"))
    for t in templates.values():
        for e in t.get("exercises", []):
            if e["name"] in latest:
                kg, lbs = latest[e["name"]]
                e["default_weight_kg"] = kg
                e["default_weight_lbs"] = lbs


def merge_exercises(session_exercises, template):
    if not template:
        return session_exercises
    pool = {e["name"]: e for e in template.get("exercises", [])}
    merged = []
    for ex in session_exercises:
        name = ex["name"]
        base = pool.get(name, {})
        if ex.get("weight_kg") or ex.get("weight_lbs"):
            weight_kg, weight_lbs = ex.get("weight_kg"), ex.get("weight_lbs")
        else:
            weight_kg, weight_lbs = base.get("default_weight_kg"), base.get("default_weight_lbs")
        merged.append({
            "name":       name,
            "weight_lbs": weight_lbs,
            "weight_kg":  weight_kg,
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


TYPE_COLORS = {
    "Upper":     "#4f8ef7",
    "Lower":     "#f7934f",
    "Full body": "#e3c04f",
    "Core":     "#f75f8f",
    "Mobility": "#4fd8f7",
    "Class":    "#a04ff7",
    "Running":  "#4ff7a0",
}
TYPE_DEFAULT = "#888"


def build_card_html(entry):
    date = entry.get("date", "-")
    day = entry.get("day", "-")
    workout_type = entry.get("type", "-")
    color = TYPE_COLORS.get(workout_type, TYPE_DEFAULT)

    if workout_type == "Running":
        duration = entry.get("duration_minutes")
        distance = entry.get("distance_km")
        pace = entry.get("pace")
        hr = entry.get("avg_heart_rate_bpm")
        calories = entry.get("calories")
        note = entry.get("note", "")
        parts = []
        if duration:
            h, m = divmod(duration, 60)
            parts.append(f"{h}h {m}min" if h else f"{m} min")
        if distance:  parts.append(f"{distance} km")
        if pace:      parts.append(f"pace {pace}")
        if note:      parts.append(note)
        detail_str = " · ".join(parts)
        extra_parts = []
        if hr:       extra_parts.append(f"❤ {hr} bpm")
        if calories: extra_parts.append(f"🔥 {calories} kcal")
        extra_str = " · ".join(extra_parts)
        detail_body = detail_str + (f"<br><small style='color:#7d8590'>{extra_str}</small>" if extra_str else "")
        return f"""
  <details class="card">
    <summary>
      <span class="date">{date}</span>
      <span class="day">{day}</span>
      <span class="badge" style="background:{color}22;color:{color};border-color:{color}44">{workout_type}</span>
      <span class="count">{detail_str}</span>
    </summary>
    <div class="class-detail">
      <span class="class-name">{detail_body}</span>
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
        if e.get("weight_kg"):
            weight = f"{e['weight_kg']} kg"
        elif e.get("weight_lbs"):
            weight = f"{e['weight_lbs']} lbs"
        else:
            weight = "-"
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
    <div class="tbl-wrap">
    <table>
      <thead><tr><th>Exercise</th><th>Weight</th><th>Sets×Reps</th><th>Note</th></tr></thead>
      <tbody>
{rows}      </tbody>
    </table>
    </div>
  </details>"""


def format_default_weight(ex):
    if ex.get("default_weight_kg"):
        return f"{ex['default_weight_kg']} kg"
    if ex.get("default_weight_lbs"):
        return f"{ex['default_weight_lbs']} lbs"
    return "-"


def build_template_section(template):
    workout_type = template.get("type", "-")
    color = TYPE_COLORS.get(workout_type, TYPE_DEFAULT)
    badge = f'<span class="badge" style="background:{color}22;color:{color};border-color:{color}44">{workout_type}</span>'

    if workout_type == "Class":
        chips = "".join(
            f'<span class="chip sel-chip" data-name="{c["name"]}">{c["name"]}'
            f'<small> · <input type="number" class="dur" '
            f'value="{c["default_duration_minutes"]}"> min</small></span>'
            for c in template.get("classes", [])
        )
        return f"""
  <div class="tpl-section">
    <div class="tpl-head">{badge}</div>
    <div class="chip-row">{chips}</div>
  </div>"""

    if workout_type == "Running":
        return f"""
  <div class="tpl-section">
    <div class="tpl-head">{badge}</div>
    <label class="run-toggle"><input type="checkbox" class="sel-run"> Log a run today</label>
    <div class="run-grid">
      <label class="run-cell">Duration (min)<input type="number" class="rfield" data-r="duration_minutes" step="1" placeholder="-"></label>
      <label class="run-cell">Distance (km)<input type="number" class="rfield" data-r="distance_km" step="0.01" placeholder="-"></label>
      <label class="run-cell">Pace (min/km)<input type="text" class="rfield" data-r="pace" placeholder="7:04"></label>
      <label class="run-cell">Avg HR (bpm)<input type="number" class="rfield" data-r="avg_heart_rate_bpm" placeholder="-"></label>
      <label class="run-cell">Calories (kcal)<input type="number" class="rfield" data-r="calories" placeholder="-"></label>
      <label class="run-cell run-note">Note<input type="text" class="rfield" data-r="note" placeholder="Zone 2 / location"></label>
    </div>
  </div>"""

    exercises = template.get("exercises", [])
    if not exercises:
        return ""
    rows = ""
    for e in exercises:
        if e.get("default_weight_kg"):
            num, unit = e["default_weight_kg"], "kg"
        elif e.get("default_weight_lbs"):
            num, unit = e["default_weight_lbs"], "lbs"
        else:
            num, unit = "", "lbs"
        lbs_sel = " selected" if unit == "lbs" else ""
        kg_sel = " selected" if unit == "kg" else ""
        sets = e.get("default_sets") or ""
        reps = e.get("default_reps") or ""
        rows += (
            f"<tr class='sel-row'>"
            f"<td class='selcell'><input type='checkbox' class='sel'></td>"
            f"<td class='exname'>{e['name']}</td>"
            f"<td class='wcell'><input type='number' class='w-num' step='0.5' value='{num}' placeholder='-'>"
            f"<select class='w-unit'><option{lbs_sel}>lbs</option><option{kg_sel}>kg</option></select></td>"
            f"<td class='srcell'><input type='number' class='sr-sets' value='{sets}'>×"
            f"<input type='number' class='sr-reps' value='{reps}'></td>"
            f"</tr>\n"
        )
    return f"""
  <div class="tpl-section">
    <div class="tpl-head">{badge}<span class="count">{len(exercises)} exercises</span></div>
    <div class="card" style="margin-top:.6rem">
      <div class="tbl-wrap">
      <table>
        <thead><tr><th></th><th>Exercise</th><th>Weight</th><th>Sets×Reps</th></tr></thead>
        <tbody data-type="{workout_type}">
{rows}        </tbody>
      </table>
      </div>
    </div>
    <button class="addrow" data-type="{workout_type}">+ Add exercise</button>
  </div>"""


TEMPLATE_ORDER = ["Upper", "Lower", "Full body", "Core", "Mobility", "Class", "Running"]

LBS_TO_KG = 0.45359237


def norm_weight_kg(ex):
    if ex.get("weight_kg"):
        return float(ex["weight_kg"])
    if ex.get("weight_lbs"):
        return float(ex["weight_lbs"]) * LBS_TO_KG
    return None


def display_weight(ex):
    if ex.get("weight_kg"):
        return f"{ex['weight_kg']:g} kg"
    if ex.get("weight_lbs"):
        return f"{ex['weight_lbs']:g} lbs"
    return "BW"


def point_from_exercise(date, ex):
    """One measurable data point, or None if the entry has no numbers at all."""
    kg = norm_weight_kg(ex)
    sets, reps = ex.get("sets"), ex.get("reps")
    work = sets * reps if (sets and reps) else None
    if kg is None and work is None:
        return None
    if kg is not None and work:
        volume = kg * work
    elif work:
        volume = work  # bodyweight: total reps
    else:
        volume = None
    if ex.get("weight_kg"):
        unit, raw = "kg", float(ex["weight_kg"])
    elif ex.get("weight_lbs"):
        unit, raw = "lbs", float(ex["weight_lbs"])
    else:
        unit, raw = None, None
    return {
        "date": date,
        "weight": display_weight(ex),
        "kg": kg,
        "unit": unit,
        "raw": raw,
        "sets": sets,
        "reps": reps,
        "work": work,
        "volume": volume,
    }


def _cmp(a, b):
    if a is None or b is None:
        return 0
    return (a > b) - (a < b)


def trend_vs_prev(prev, cur):
    """Compare two points → (css_class, label). Weight decides; ties fall to sets×reps.
    Label shows the weight delta when weight changed, else the volume/reps delta."""
    if prev is None:
        return "new", "● new"
    if prev["kg"] is not None and cur["kg"] is not None:
        d = _cmp(cur["kg"], prev["kg"])
        if d:
            if prev["unit"] == cur["unit"]:
                delta = f"{cur['raw'] - prev['raw']:+g} {cur['unit']}"
            else:
                delta = f"{cur['kg'] - prev['kg']:+.1f} kg"
            return ("up", f"▲ {delta}") if d > 0 else ("down", f"▼ {delta}")
        d = _cmp(cur["work"], prev["work"])
    elif prev["kg"] is None and cur["kg"] is not None:
        return "up", "▲ +weight"   # bodyweight → added weight
    elif prev["kg"] is not None and cur["kg"] is None:
        return "down", "▼ −weight"  # weighted → bodyweight
    else:
        d = _cmp(cur["work"], prev["work"])
    pct = None
    if prev["volume"] and cur["volume"] is not None:
        pct = round((cur["volume"] - prev["volume"]) / prev["volume"] * 100)
    if d > 0:
        return "up", f"▲ {pct:+d}%" if pct is not None else "▲ up"
    if d < 0:
        return "down", f"▼ {pct:+d}%" if pct is not None else "▼ down"
    return "flat", "— same"


def collect_progress(raw_entries, templates):
    """Group completed strength exercises by name, oldest→newest, raw logged data only."""
    name_type = {}
    for t in TEMPLATE_ORDER:
        for e in templates.get(t, {}).get("exercises", []):
            name_type.setdefault(e["name"], t)
    history = {}
    for entry in sorted(raw_entries, key=lambda e: e.get("date", "")):
        if entry.get("type") in ("Class", "Running"):
            continue
        for ex in entry.get("exercises", []):
            if not ex.get("completed"):
                continue
            point = point_from_exercise(entry.get("date", ""), ex)
            if point is None:
                continue
            name = ex["name"]
            history.setdefault(name, {"points": [], "type": None})
            history[name]["points"].append(point)
            history[name]["type"] = name_type.get(name, entry.get("type", "-"))
    return history


def build_sparkline(points):
    vols = [p["volume"] for p in points if p["volume"] is not None][-10:]
    if len(vols) < 2:
        return ""
    w, h, pad = 88, 26, 5
    lo, hi = min(vols), max(vols)
    span = (hi - lo) or 1
    xs = [pad + i * (w - 2 * pad) / (len(vols) - 1) for i in range(len(vols))]
    ys = [h - pad - (v - lo) / span * (h - 2 * pad) for v in vols]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    return (
        f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true">'
        f'<polyline points="{poly}" fill="none" stroke="#5e6ad2" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="4" fill="#5e6ad2" '
        f'stroke="#0f1014" stroke-width="2"/></svg>'
    )


def format_volume(p):
    if p["volume"] is None:
        return "-"
    if p["kg"] is None:
        return f"{p['volume']:g} reps"
    return f"{p['volume']:g} kg"


def build_progress_card(name, data):
    points = data["points"]
    workout_type = data["type"]
    color = TYPE_COLORS.get(workout_type, TYPE_DEFAULT)
    latest = points[-1]
    prev = points[-2] if len(points) > 1 else None
    cls, label = trend_vs_prev(prev, latest)

    rows = ""
    for i in range(len(points) - 1, -1, -1):
        p = points[i]
        p_prev = points[i - 1] if i > 0 else None
        d_cls, d_label = trend_vs_prev(p_prev, p)
        sr = f"{p['sets']}×{p['reps']}" if p["work"] else "-"
        rows += (
            f"<tr>"
            f"<td>{p['date']}</td>"
            f"<td>{p['weight']}</td>"
            f"<td>{sr}</td>"
            f"<td>{format_volume(p)}</td>"
            f"<td><span class='trend {d_cls}'>{d_label}</span></td>"
            f"</tr>\n"
        )

    sr_latest = f"{latest['sets']}×{latest['reps']}" if latest["work"] else ""
    latest_str = " · ".join(s for s in (latest["weight"], sr_latest, latest["date"]) if s)
    badge = (f'<span class="badge" style="background:{color}22;color:{color};'
             f'border-color:{color}44">{workout_type}</span>')
    return f"""
  <details class="card prog-card" data-type="{workout_type}">
    <summary>
      <div class="prog-main">
        <div class="prog-head"><span class="prog-name">{name}</span>{badge}</div>
        <div class="prog-latest">{latest_str}</div>
      </div>
      {build_sparkline(points)}
      <span class="trend {cls}">{label}</span>
    </summary>
    <div class="tbl-wrap">
    <table>
      <thead><tr><th>Date</th><th>Weight</th><th>Sets×Reps</th><th>Volume</th><th>Δ</th></tr></thead>
      <tbody>
{rows}      </tbody>
    </table>
    </div>
  </details>"""


def build_progress_view(raw_entries, templates, compact=False):
    history = collect_progress(raw_entries, templates)
    if not history:
        return "<p class='section-title'>No strength data yet</p>"

    ordered = sorted(history.items(), key=lambda kv: kv[1]["points"][-1]["date"], reverse=True)

    last_date = ordered[0][1]["points"][-1]["date"]
    last_names = [(n, d) for n, d in ordered if d["points"][-1]["date"] == last_date]
    last_types = sorted({d["type"] for _, d in last_names})
    up = sum(
        1 for _, d in last_names
        if trend_vs_prev(d["points"][-2] if len(d["points"]) > 1 else None, d["points"][-1])[0] == "up"
    )
    stats = f"""
  <div class="stats">
    <div class="stat">
      <div class="stat-label">Last session</div>
      <div class="stat-value">{last_date}</div>
      <div class="stat-sub">{" / ".join(last_types)} · {len(last_names)} exercises</div>
    </div>
    <div class="stat">
      <div class="stat-label">Progressive overload</div>
      <div class="stat-value">{up}<small>/{len(last_names)}</small></div>
      <div class="stat-sub">▲ vs previous session</div>
    </div>
    <div class="stat">
      <div class="stat-label">Tracked</div>
      <div class="stat-value">{len(history)}</div>
      <div class="stat-sub">exercises with data</div>
    </div>
  </div>"""

    types_present = sorted({d["type"] for _, d in ordered},
                           key=lambda t: TEMPLATE_ORDER.index(t) if t in TEMPLATE_ORDER else 99)
    chips = '<span class="chip filter-chip selected" data-filter="all">All</span>'
    chips += "".join(
        f'<span class="chip filter-chip" data-filter="{t}">{t}</span>' for t in types_present
    )
    cards = "\n".join(build_progress_card(n, d) for n, d in ordered)
    if compact:
        return f"""
  <div class="chip-row" id="prog-filters">{chips}</div>
{cards}"""
    return f"""{stats}
  <div class="chip-row" id="prog-filters">{chips}</div>
  <p class="section-title" style="margin-top:1.25rem">Latest first — tap a card for full history</p>
{cards}"""

SAVE_CSS = """
    .selcell { width: 2.2rem; }
    .sel, .sel-run {
      width: 1.1rem; height: 1.1rem; accent-color: #e3b341;
      cursor: pointer; vertical-align: middle;
    }
    .sel-row { cursor: pointer; }
    .sel-chip {
      cursor: pointer; font-family: inherit;
      transition: all .15s;
    }
    .sel-chip.selected {
      background: #e3b34122; border-color: #e3b34166; color: #e3b341;
    }
    .sel-chip.selected small { color: #e3b341aa; }
    #savebar {
      position: fixed; bottom: 0; left: 0; right: 0;
      display: none; align-items: center; justify-content: center; gap: 1rem;
      padding: .9rem 1rem calc(.9rem + env(safe-area-inset-bottom));
      background: #161b22ee; border-top: 1px solid #30363d;
      backdrop-filter: blur(8px);
    }
    #savebar.visible { display: flex; }
    #savecount { font-size: .85rem; color: #7d8590; }
    #savebtn {
      background: #238636; border: none; color: #fff;
      font-size: .9rem; font-weight: 600; font-family: inherit;
      padding: .55rem 1.6rem; border-radius: 8px; cursor: pointer;
    }
    #savebtn:disabled { opacity: .5; cursor: wait; }
    #tokenbtn {
      background: none; border: 1px solid #30363d; color: #7d8590;
      border-radius: 8px; padding: .5rem .7rem; cursor: pointer; font-family: inherit;
    }
    .wcell input, .srcell input, .exname input, .dur, .rfield {
      background: #0d1117; border: 1px solid #30363d; color: #e6edf3;
      border-radius: 6px; padding: .28rem .4rem;
      font-size: .85rem; font-family: inherit;
    }
    .rfield { width: 100%; }
    .run-toggle { display: flex; align-items: center; gap: .5rem; margin-top: .6rem; font-size: .85rem; color: #c9d1d9; cursor: pointer; }
    .run-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: .6rem; margin-top: .6rem; }
    .run-cell { display: flex; flex-direction: column; gap: .25rem; font-size: .72rem; color: #7d8590; }
    .run-note { grid-column: 1 / -1; }
    .w-num { width: 4.4rem; }
    .sr-sets, .sr-reps { width: 3rem; text-align: center; }
    .srcell { white-space: nowrap; }
    .exname input { width: 10rem; }
    .dur { width: 3.6rem; padding: .1rem .3rem; font-size: .8rem; }
    .w-unit {
      background: #0d1117; color: #7d8590; border: 1px solid #30363d;
      border-radius: 6px; padding: .28rem .2rem; font-size: .8rem;
      font-family: inherit; margin-left: .3rem;
    }
    input[type=number] { appearance: textfield; -moz-appearance: textfield; }
    input[type=number]::-webkit-inner-spin-button { -webkit-appearance: none; }
    .addrow {
      background: none; border: 1px dashed #30363d; color: #7d8590;
      border-radius: 8px; padding: .45rem 1rem; margin-top: .6rem;
      font-size: .82rem; font-family: inherit; cursor: pointer;
    }
    .addrow:hover { border-color: #484f58; color: #c9d1d9; }
    .more-hidden { display: none; }
    #viewmore {
      display: block; width: 100%; margin-top: .5rem;
      background: none; border: 1px solid #30363d; color: #58a6ff;
      border-radius: 10px; padding: .7rem; cursor: pointer;
      font-size: .85rem; font-weight: 600; font-family: inherit;
    }
    #viewmore:hover { border-color: #484f58; background: #161b22; }
"""

PROGRESS_CSS = """
    .stats {
      display: grid; grid-template-columns: repeat(3, 1fr);
      gap: .75rem; margin-bottom: 1.25rem;
    }
    .stat {
      background: #161b22; border: 1px solid #30363d;
      border-radius: 10px; padding: .8rem 1rem; min-width: 0;
    }
    .stat-label {
      font-size: .68rem; font-weight: 600; letter-spacing: .06em;
      text-transform: uppercase; color: #7d8590;
    }
    .stat-value { font-size: 1.3rem; font-weight: 700; color: #f0f6fc; margin-top: .15rem; }
    .stat-value small { font-size: .85rem; font-weight: 600; color: #7d8590; }
    .stat-sub { font-size: .74rem; color: #7d8590; margin-top: .1rem; }
    .filter-chip { cursor: pointer; transition: all .15s; user-select: none; }
    .filter-chip.selected { background: #1f6feb22; border-color: #1f6feb66; color: #58a6ff; }
    .prog-main { flex: 1; min-width: 0; }
    .prog-head { display: flex; align-items: center; gap: .6rem; }
    .prog-name {
      font-size: .92rem; font-weight: 600; color: #e6edf3;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .prog-latest { font-size: .76rem; color: #7d8590; margin-top: .2rem; }
    .spark { flex-shrink: 0; }
    .trend {
      font-size: .8rem; font-weight: 600; white-space: nowrap;
      flex-shrink: 0; min-width: 4.3rem; text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .trend.up   { color: #3fb950; }
    .trend.down { color: #f85149; }
    .trend.flat { color: #7d8590; }
    .trend.new  { color: #58a6ff; }
    td .trend { min-width: 0; text-align: left; }
    @media (max-width: 480px) {
      .stats { grid-template-columns: 1fr 1fr; }
      .stat:first-child { grid-column: 1 / -1; }
      .spark { display: none; }
    }
"""

PROGRESS_SCRIPT = """
    document.querySelectorAll('.filter-chip').forEach(ch =>
      ch.addEventListener('click', () => {
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('selected'));
        ch.classList.add('selected');
        const f = ch.dataset.filter;
        document.querySelectorAll('.prog-card').forEach(card => {
          card.style.display = (f === 'all' || card.dataset.type === f) ? '' : 'none';
        });
      }));
"""

SAVE_SCRIPT = """
    const REPO = 'MethawiPhokhai/GymRecording';
    const BRANCH = 'claude/session-summary-ffzuxy';
    const API = `https://api.github.com/repos/${REPO}/contents/`;

    const savebar = document.getElementById('savebar');
    const savecount = document.getElementById('savecount');
    const savebtn = document.getElementById('savebtn');

    function rowData(cb) {
      const tr = cb.closest('tr');
      const type = tr.closest('tbody').dataset.type;
      const nameEl = tr.querySelector('.exname input') || tr.querySelector('.exname');
      const name = (nameEl.value !== undefined ? nameEl.value : nameEl.textContent).trim();
      const ex = { name, completed: true };
      const w = parseFloat(tr.querySelector('.w-num').value);
      if (w > 0) {
        const unit = tr.querySelector('.w-unit').value;
        if (unit === 'kg') ex.weight_kg = w; else ex.weight_lbs = w;
      }
      const sets = parseInt(tr.querySelector('.sr-sets').value);
      const reps = parseInt(tr.querySelector('.sr-reps').value);
      if (sets > 0) ex.sets = sets;
      if (reps > 0) ex.reps = reps;
      return { kind: 'exercise', type, ex };
    }

    function selections() {
      const items = [];
      document.querySelectorAll('.sel:checked').forEach(cb => {
        const d = rowData(cb);
        if (d.ex.name) items.push(d);
      });
      document.querySelectorAll('.sel-chip.selected').forEach(ch =>
        items.push({ kind: 'class', name: ch.dataset.name,
                     duration: parseInt(ch.querySelector('.dur').value) || null }));
      const runCb = document.querySelector('.sel-run');
      if (runCb && runCb.checked) {
        const run = { kind: 'running' };
        document.querySelectorAll('.rfield').forEach(f => {
          const k = f.dataset.r;
          let v = f.value.trim();
          if (!v) return;
          if (k === 'pace') {
            if (!v.includes('min/km')) v = v + ' min/km';
            run[k] = v;
          } else if (k === 'note') {
            run[k] = v;
          } else {
            run[k] = Number(v);
          }
        });
        items.push(run);
      }
      return items;
    }

    function refreshBar() {
      const n = selections().length;
      savecount.textContent = n + ' selected';
      savebar.classList.toggle('visible', n > 0);
    }

    function bindRow(row) {
      row.addEventListener('click', e => {
        if (e.target.matches('input, select, button')) return;
        const cb = row.querySelector('.sel');
        cb.checked = !cb.checked;
        refreshBar();
      });
      row.querySelector('.sel').addEventListener('change', refreshBar);
    }

    document.querySelectorAll('.sel-row').forEach(bindRow);

    document.querySelectorAll('.sel-chip').forEach(ch =>
      ch.addEventListener('click', e => {
        if (e.target.matches('input')) return;
        ch.classList.toggle('selected');
        refreshBar();
      }));

    const runToggle = document.querySelector('.sel-run');
    if (runToggle) runToggle.addEventListener('change', refreshBar);

    document.querySelectorAll('.addrow').forEach(btn =>
      btn.addEventListener('click', () => {
        const tbody = btn.closest('.tpl-section').querySelector('tbody');
        const tr = document.createElement('tr');
        tr.className = 'sel-row';
        tr.innerHTML = `
          <td class='selcell'><input type='checkbox' class='sel' checked></td>
          <td class='exname'><input type='text' placeholder='Exercise name'></td>
          <td class='wcell'><input type='number' class='w-num' step='0.5' placeholder='-'>
            <select class='w-unit'><option>lbs</option><option>kg</option></select></td>
          <td class='srcell'><input type='number' class='sr-sets' value='3'>×<input type='number' class='sr-reps' value='15'></td>`;
        tbody.appendChild(tr);
        bindRow(tr);
        tr.querySelector('.exname input').focus();
        refreshBar();
      }));

    function getToken(force) {
      let t = localStorage.getItem('gh_token');
      if (!t || force) {
        t = prompt('Paste GitHub fine-grained token (Contents: Read and write on GymRecording). Stored only in this browser.');
        if (t) localStorage.setItem('gh_token', t.trim());
      }
      return t;
    }

    document.getElementById('tokenbtn').addEventListener('click', () => getToken(true));

    const viewmore = document.getElementById('viewmore');
    if (viewmore) viewmore.addEventListener('click', () => {
      document.querySelectorAll('.more-hidden').forEach((c, i) => {
        if (i < 10) c.classList.remove('more-hidden');
      });
      if (!document.querySelector('.more-hidden')) viewmore.style.display = 'none';
    });

    const b64 = s => btoa(unescape(encodeURIComponent(s)));
    const unb64 = s => decodeURIComponent(escape(atob(s)));

    async function ghGet(path, token) {
      const r = await fetch(API + path + '?ref=' + BRANCH, {
        headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' }
      });
      if (r.status === 404) return null;
      if (!r.ok) throw new Error('GET ' + path + ': ' + r.status);
      return r.json();
    }

    async function ghPut(path, obj, sha, token) {
      const body = {
        message: 'log: add workout via web',
        content: b64(JSON.stringify(obj, null, 2) + '\\n'),
        branch: BRANCH
      };
      if (sha) body.sha = sha;
      const r = await fetch(API + path, {
        method: 'PUT',
        headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' },
        body: JSON.stringify(body)
      });
      if (!r.ok) throw new Error('PUT ' + path + ': ' + r.status);
    }

    savebtn.addEventListener('click', async () => {
      const items = selections();
      if (!items.length) return;
      const token = getToken(false);
      if (!token) return;

      const opts = { timeZone: 'Asia/Bangkok' };
      const date = new Date().toLocaleDateString('en-CA', opts);
      const dayName = new Date().toLocaleDateString('en-US', { weekday: 'long', ...opts });

      savebtn.disabled = true;
      savebtn.textContent = 'Saving…';
      try {
        const byType = {};
        items.filter(i => i.kind === 'exercise').forEach(i => {
          (byType[i.type] = byType[i.type] || []).push(i.ex);
        });

        for (const [type, exs] of Object.entries(byType)) {
          const path = `workouts/${date}-${type.toLowerCase().replace(/\\s+/g, '')}-web.json`;
          const existing = await ghGet(path, token);
          let obj, sha = null;
          if (existing) {
            obj = JSON.parse(unb64(existing.content));
            sha = existing.sha;
            exs.forEach(ex => {
              const idx = obj.exercises.findIndex(e => e.name === ex.name);
              if (idx >= 0) obj.exercises[idx] = ex;
              else obj.exercises.push(ex);
            });
          } else {
            obj = { date, day: dayName, type, exercises: exs };
          }
          await ghPut(path, obj, sha, token);
        }

        for (const c of items.filter(i => i.kind === 'class')) {
          const slug = c.name.toLowerCase().replace(/\\s+/g, '');
          const path = `workouts/${date}-class-${slug}.json`;
          const existing = await ghGet(path, token);
          const obj = { date, day: dayName, type: 'Class',
                        name: c.name, duration_minutes: c.duration };
          await ghPut(path, obj, existing ? existing.sha : null, token);
        }

        for (const r of items.filter(i => i.kind === 'running')) {
          let n = 1, runPath, runExisting;
          while (true) {
            runPath = n === 1
              ? `workouts/${date}-running-web.json`
              : `workouts/${date}-running-web-${n}.json`;
            runExisting = await ghGet(runPath, token);
            if (!runExisting) break;
            n++;
          }
          const runObj = { date, day: dayName, type: 'Running' };
          Object.keys(r).forEach(k => { if (k !== 'kind') runObj[k] = r[k]; });
          await ghPut(runPath, runObj, null, token);
        }

        document.querySelectorAll('.sel:checked').forEach(cb => cb.checked = false);
        document.querySelectorAll('.sel-chip.selected').forEach(ch => ch.classList.remove('selected'));
        const runClear = document.querySelector('.sel-run');
        if (runClear) runClear.checked = false;
        document.querySelectorAll('.rfield').forEach(f => f.value = '');
        refreshBar();
        alert('Saved! The site rebuilds in ~1 minute, then pull to refresh.');
      } catch (err) {
        if (String(err).includes('401') || String(err).includes('403')) {
          alert('Token invalid or expired — tap ⚙ to set a new one.');
        } else {
          alert('Save failed: ' + err.message);
        }
      } finally {
        savebtn.disabled = false;
        savebtn.textContent = 'Save to Log';
      }
    });
"""


PAGE_SIZE = 10

#!/usr/bin/env python3
# New tail for build.py — replaces build_html with a Design-3 (Linear-style) dashboard,
# keeping all data functions + SAVE_SCRIPT + PROGRESS_SCRIPT intact.

from datetime import date as _date, timedelta


STRENGTH_TYPES = {"Upper", "Lower", "Full body", "Core", "Mobility"}


def compute_summary(entries, raw_entries):
    """Derive dashboard stats for the header strip from real logged data."""
    dates = sorted({e.get("date") for e in raw_entries if e.get("date")}, reverse=True)

    # Window = 30 days back from the latest workout
    cutoff = None
    if dates:
        try:
            cutoff = (_date.fromisoformat(dates[0]) - timedelta(days=29)).isoformat()
        except Exception:
            cutoff = None
    recent = [e for e in raw_entries if e.get("date") and (not cutoff or e["date"] >= cutoff)]

    sessions = len(recent)  # each logged workout = 1 session (weight + cardio add up)
    weight = sum(1 for e in recent if e.get("type") in STRENGTH_TYPES)
    cardio = sum(1 for e in recent if e.get("type") not in STRENGTH_TYPES)
    distance = sum((e.get("distance_km") or 0) for e in recent if e.get("type") == "Running")
    total_sessions = len({e.get("date") for e in raw_entries})

    return {
        "last30": sessions,
        "weight": weight,
        "cardio": cardio,
        "distance": distance,
        "total": total_sessions,
    }


def build_statgrid(entries, raw_entries):
    s = compute_summary(entries, raw_entries)
    dist_disp = f"{s['distance']:.1f}" if s["distance"] else "0"
    return f"""
    <div class="statgrid">
      <div class="stat"><div class="k">Last 30 days</div><div class="v">{s['last30']}</div><div class="d">total sessions</div></div>
      <div class="stat"><div class="k">Weight training</div><div class="v">{s['weight']}</div><div class="d">sessions · 30d</div></div>
      <div class="stat"><div class="k">Cardio</div><div class="v">{s['cardio']}</div><div class="d">sessions · 30d</div></div>
      <div class="stat"><div class="k">Run distance</div><div class="v">{dist_disp}&nbsp;km</div><div class="d">last 30 days</div></div>
    </div>"""


STYLE = """
  :root{
    --bg:#08090c; --panel:#0f1014; --panel2:#14151a; --hover:#1a1c22;
    --line:#22242b; --line2:#2c2f38; --ink:#f2f3f7; --mut:#8a8f9c; --dim:#5b6070;
    --accent:#5e6ad2; --accent2:#7a86ff; --green:#4dd0a9; --orange:#f7a35c; --red:#f16b5f;
    --mono:'JetBrains Mono','SFMono-Regular',ui-monospace,Menlo,Consolas,monospace;
    --radius:10px;
  }
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  html{-webkit-text-size-adjust:100%}
  body{background:var(--bg);color:var(--ink);font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;line-height:1.45;-webkit-font-smoothing:antialiased}
  button{font-family:inherit;cursor:pointer;border:none;background:none;color:inherit}
  a{color:inherit;text-decoration:none}
  .layout{min-height:100vh}

  /* ---- Slide-out drawer (replaces desktop sidebar) ---- */
  .side{position:fixed;top:0;left:0;bottom:0;width:250px;background:var(--panel);border-right:1px solid var(--line);padding:16px 12px calc(16px + env(safe-area-inset-bottom));display:flex;flex-direction:column;gap:2px;transform:translateX(-105%);transition:transform .22s ease;z-index:60;overflow:auto}
  .side.open{transform:translateX(0)}
  .side .brand{display:flex;align-items:center;gap:9px;padding:4px 10px 18px;font-weight:700;font-size:13.5px;letter-spacing:-.01em}
  .side .brand .logo{width:20px;height:20px;border-radius:6px;background:linear-gradient(135deg,var(--accent),var(--accent2))}
  .side a{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:8px;color:var(--mut);font-size:13px;font-weight:550}
  .side a svg{width:16px;height:16px;flex:none}
  .side a.on{background:var(--hover);color:var(--ink)}
  .side a:hover{background:var(--hover);color:var(--ink)}
  .side hr{border:none;border-top:1px solid var(--line);margin:12px 8px}
  .side .foot{padding:10px 12px;font-size:10.5px;color:var(--dim);margin-top:auto}
  .side .foot b{display:block;color:var(--mut);font-weight:600}
  .overlay{position:fixed;inset:0;background:rgba(0,0,0,.5);opacity:0;pointer-events:none;transition:opacity .2s;z-index:55}
  .overlay.show{opacity:1;pointer-events:auto}

  /* ---- Hamburger menu button ---- */
  .hamburger{display:none;align-items:center;justify-content:center;border:1px solid var(--line2);background:var(--panel2);color:var(--ink);border-radius:8px;padding:8px 12px}
  .hamburger:hover{border-color:var(--accent)}
  .hamburger svg{width:18px;height:18px}

  /* ---- Mobile bottom nav ---- */
  .bmob{position:fixed;left:0;right:0;bottom:0;background:rgba(8,9,12,.94);backdrop-filter:blur(10px);border-top:1px solid var(--line);display:grid;grid-template-columns:repeat(2,1fr);z-index:30}
  .bmob button{color:var(--mut);font-size:10.5px;font-weight:600;padding:12px 0 14px;display:flex;flex-direction:column;align-items:center;gap:4px}
  .bmob button.on{color:var(--accent)}
  .bmob svg{width:20px;height:20px}

  /* ---- Main ---- */
  .main{width:100%;max-width:1500px;margin:0 auto;padding:18px 18px 92px}
  .view{display:none}
  .view.on{display:block}
  .dash-cols{display:block}
  .dash-cols section{min-width:0}
  .topbar{display:flex;align-items:center;justify-content:space-between;gap:10px;padding-bottom:16px}
  .topbar h1{font-size:17px;font-weight:700;letter-spacing:-.02em;margin:0}
  .topbar .meta{font-size:12px;color:var(--mut);margin-top:2px}
  .topbar .actions{display:flex;gap:8px}

  .statgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
  .stat{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:13px 15px}
  .stat .k{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em;font-weight:600}
  .stat .v{font-family:var(--mono);font-size:22px;font-weight:700;letter-spacing:-.02em;margin-top:6px}
  .stat .d{font-size:11.5px;color:var(--mut);margin-top:2px}

  .section-title{font-size:12px;font-weight:700;color:var(--mut);text-transform:uppercase;letter-spacing:.07em;margin:20px 0 12px}

  /* ---- Tables ---- */
  .tbl-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;background:var(--panel);border:1px solid var(--line);border-radius:var(--radius)}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th{text-align:left;color:var(--dim);font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;padding:10px 14px 8px;border-bottom:1px solid var(--line);font-weight:600;white-space:nowrap}
  td{padding:9px 14px;border-bottom:1px solid #16171c;color:var(--ink)}
  tbody tr:hover td{background:var(--hover)}
  .num{text-align:right;font-family:var(--mono);color:var(--mut);font-size:12px}
  td.note{color:var(--orange);font-size:12px}
  .trend{font-weight:600;white-space:nowrap;font-variant-numeric:tabular-nums;font-size:12px}
  .trend.up{color:var(--green)} .trend.down{color:var(--red)} .trend.flat{color:var(--dim)} .trend.new{color:var(--accent2)}

  /* ---- Log cards (details) ---- */
  .card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);margin-bottom:9px;overflow:hidden}
  .card:hover{border-color:var(--line2)}
  .card summary{display:flex;align-items:center;gap:12px;padding:13px 15px;cursor:pointer;list-style:none;user-select:none;flex-wrap:wrap}
  .card summary::-webkit-details-marker{display:none}
  .card summary::before{content:'';flex:none;border:5.5px solid transparent;border-left:8px solid var(--dim);transition:transform .18s}
  .card[open] summary::before{transform:rotate(90deg)}
  .date{font-family:var(--mono);font-size:12.5px;color:var(--mut);min-width:78px}
  .day{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.05em;flex:none;width:34px}
  .badge{font-size:10.5px;font-weight:700;padding:2.5px 9px;border-radius:20px;border:1px solid;flex:none;letter-spacing:.02em;margin-left:auto}
  .count{font-size:12.5px;color:var(--mut);text-align:right;font-variant-numeric:tabular-nums}
  .detail{padding:4px 15px 15px;border-top:1px solid var(--line)}
  .detail .tbl-wrap{margin-top:12px}
  .class-detail{padding:12px 15px 15px 30px;display:flex;align-items:center;gap:8px}
  .class-name{font-size:14px;font-weight:600}
  .class-duration{font-size:12px;color:var(--mut)}
  .more-hidden{display:none}

  /* ---- Header chrome (Log view) ---- */
  .headline{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:6px}
  .headline .title{font-size:15px;font-weight:700;letter-spacing:-.01em}

  /* ---- Progress ---- */
  .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px}
  .stats .stat-label{font-size:10.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--mut)}
  .stats .stat-value{font-size:20px;font-weight:700;color:var(--ink);margin-top:4px;font-family:var(--mono)}
  .stats .stat-value small{font-size:12px;font-weight:600;color:var(--mut)}
  .stats .stat-sub{font-size:11.5px;color:var(--mut);margin-top:2px}
  .chip-row{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0}
  .chip{background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:6px 14px;font-size:12.5px;color:var(--mut);cursor:pointer;user-select:none;transition:.15s}
  .chip:hover{border-color:var(--line2);color:var(--ink)}
  .chip small{color:var(--dim)}
  .filter-chip.selected{background:var(--accent);border-color:var(--accent);color:#fff}
  .prog-card .tbl-wrap{margin-top:12px}
  .prog-main{flex:1;min-width:0}
  .prog-head{display:flex;align-items:center;gap:8px}
  .prog-name{font-size:13.5px;font-weight:650;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .prog-latest{font-size:11.5px;color:var(--mut);margin-top:2px}
  .spark{flex-shrink:0}

  /* ---- Templates / save form ---- */
  .tpl-section{margin-bottom:16px}
  .tpl-head{display:flex;align-items:center;gap:9px;padding:4px 0 2px}
  .tpl-head .t{font-weight:700;font-size:14px;color:var(--ink)}
  .tpl-count{font-size:11.5px;color:var(--mut)}
  .selcell{width:2.2rem}
  .sel,.sel-run{width:1.05rem;height:1.05rem;accent-color:var(--accent);cursor:pointer;vertical-align:middle}
  .sel-row{cursor:pointer}
  .sel-chip{cursor:pointer;transition:.15s;user-select:none}
  .sel-chip.selected{background:var(--accent);border-color:var(--accent);color:#fff}
  .sel-chip.selected small{color:#fff}
  .wcell input,.srcell input,.exname input,.dur,.rfield,input.rv{
    background:var(--panel2);border:1px solid var(--line);color:var(--ink);
    border-radius:6px;padding:6px 8px;font-size:12.5px;font-family:inherit;min-width:0
  }
  .wcell input:focus,.srcell input:focus,.exname input:focus,.dur:focus,.rfield:focus,input.rv:focus{
    outline:none;border-color:var(--accent)
  }
  .rfield{width:100%}
  .w-num{width:4.2rem}
  .sr-sets,.sr-reps{width:2.6rem;text-align:center}
  .srcell{white-space:nowrap}
  .exname input{width:9rem}
  .dur{width:3.4rem;padding:4px 6px;font-size:12px}
  .w-unit{background:var(--panel2);color:var(--mut);border:1px solid var(--line);border-radius:6px;padding:6px 4px;font-size:12px;font-family:inherit;margin-left:4px}
  input[type=number]{appearance:textfield;-moz-appearance:textfield}
  input[type=number]::-webkit-inner-spin-button{-webkit-appearance:none}
  .addrow{background:none;border:1px dashed var(--line2);color:var(--mut);border-radius:8px;padding:10px 14px;margin-top:8px;font-size:12.5px;font-family:inherit;cursor:pointer;width:100%}
  .addrow:hover{border-color:var(--accent);color:var(--ink)}
  .run-toggle{display:flex;align-items:center;gap:8px;margin-top:8px;font-size:13px;color:var(--ink);cursor:pointer}
  .run-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:8px}
  .run-cell{display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--mut)}
  .run-note{grid-column:1 / -1}
  .note-row{display:flex;gap:8px;align-items:center;font-size:11px;color:var(--mut)}

  /* ---- Save bar ---- */
  #savebar{position:fixed;bottom:0;left:0;right:0;display:none;align-items:center;justify-content:center;gap:14px;padding:11px 16px calc(11px + env(safe-area-inset-bottom));background:rgba(15,16,20,.95);border-top:1px solid var(--line);backdrop-filter:blur(10px);z-index:40}
  #savebar.visible{display:flex}
  #savecount{font-size:12.5px;color:var(--mut)}
  #savebtn{background:var(--accent);border:none;color:#fff;font-size:13px;font-weight:650;font-family:inherit;padding:9px 20px;border-radius:8px}
  #savebtn:hover{filter:brightness(1.1)}
  #savebtn:disabled{opacity:.5;cursor:wait}
  #tokenbtn{background:var(--panel2);border:1px solid var(--line);color:var(--mut);border-radius:8px;padding:9px 12px}

  #view-more,.view-more,.btn{border:1px solid var(--line2);background:var(--panel2);color:var(--ink);border-radius:8px;padding:9px 14px;font-size:12.5px;font-weight:600}
  #view-more:hover,.view-more:hover,.btn:hover{border-color:var(--accent)}
  #view-more,.view-more{display:block;width:100%;margin-top:10px}
  .btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}

  /* pull-to-refresh */
  #ptr-indicator{display:flex;align-items:center;justify-content:center;height:0;overflow:hidden;transition:height .2s;color:var(--mut);font-size:12px;gap:8px}
  #ptr-indicator.visible{height:48px}
  #ptr-indicator svg{animation:spin 1s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}

  footer{margin:28px 0 8px;text-align:center;font-size:11.5px;color:var(--dim)}

  /* responsive */
  @media(min-width:900px){
    .bmob{display:none}
    .hamburger{display:inline-flex}
    .main{width:80%;max-width:1500px;padding:22px 28px 40px}
    .statgrid{grid-template-columns:repeat(4,1fr)}
    .stats{grid-template-columns:repeat(3,1fr)}
    .dash-cols{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;align-items:start}
    #savebar{bottom:0}
  }
  @media(max-width:480px){
    .statgrid{grid-template-columns:1fr 1fr}
    .stats{grid-template-columns:1fr 1fr}
    .stats .stat:first-child{grid-column:1 / -1}
    .spark{display:none}
    .date{min-width:64px}
  }
"""


def build_html(entries, templates, raw_entries):
    progress_view = build_progress_view(raw_entries, templates, compact=True)

    def col(col_entries):
        lst = [build_card_html(e) for e in col_entries]
        lst = [
            c if i < PAGE_SIZE else c.replace('<details class="card">', '<details class="card more-hidden">', 1)
            for i, c in enumerate(lst)
        ]
        more = f'<button class="view-more">View more</button>' if len(col_entries) > PAGE_SIZE else ""
        return "\n".join(lst), more

    weight = [e for e in entries if e.get("type") in STRENGTH_TYPES]
    cardio = [e for e in entries if e.get("type") not in STRENGTH_TYPES]
    weight_cards, weight_more = col(weight)
    cardio_cards, cardio_more = col(cardio)
    ordered = [templates[t] for t in TEMPLATE_ORDER if t in templates]
    ordered += [t for k, t in templates.items() if k not in TEMPLATE_ORDER]
    template_sections = "\n".join(
        s for s in (build_template_section(t) for t in ordered) if s
    )
    statgrid = build_statgrid(entries, raw_entries)

    latest_date = entries[0].get("date", "—") if entries else "—"
    n = len(entries)
    updated = datetime.now(BKK).strftime("%Y-%m-%d %H:%M (Bangkok)")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Gym Recording</title>
  <style>{STYLE}</style>
</head>
<body>
  <div id="ptr-indicator">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
    </svg>
    Refreshing…
  </div>
  <div class="layout">
    <aside class="side">
      <div class="brand"><span class="logo"></span> Gym Recording</div>
      <a class="on" data-view="dashboard" href="#">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>Dashboard
      </a>
      <a data-view="templates" href="#">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/></svg>Plan
      </a>
      <hr>
      <a href="#">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/></svg>Settings
      </a>
      <div class="foot"><b>{n} workouts</b>updated {updated}</div>
    </aside>
    <div class="overlay" id="overlay"></div>

    <div class="main">
      <div class="topbar">
        <div><h1 id="page-title">Dashboard</h1><div class="meta">latest session {latest_date}</div></div>
        <div class="actions">
          <button class="hamburger" id="menu-btn" aria-label="Menu"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg></button>
        </div>
      </div>

      <div id="view-dashboard" class="view on">
        {statgrid}
        <div class="dash-cols">
          <section>
            <div class="section-title">Weight training</div>
            {weight_cards}
            {weight_more}
          </section>
          <section>
            <div class="section-title">Cardio</div>
            {cardio_cards}
            {cardio_more}
          </section>
          <section>
            <div class="section-title">Progress</div>
            {progress_view}
          </section>
        </div>
      </div>

      <div id="view-templates" class="view">
        <div class="section-title">Select exercises to log</div>
        <p style="color:var(--mut);font-size:13px;margin-bottom:14px">Tick the exercises you did — the save bar appears at the bottom.</p>
        {template_sections}
        <div style="height:5rem"></div>
      </div>

      <footer>Updated {updated}</footer>
    </div>
  </div>

  <nav class="bmob">
    <button class="on" data-view="dashboard"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>Dashboard</button>
    <button data-view="templates"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/></svg>Plan</button>
  </nav>

  <div id="savebar">
    <span id="savecount"></span>
    <button id="savebtn">Save to Log</button>
    <button id="tokenbtn" title="Set GitHub token">⚙</button>
  </div>

  <script>{SAVE_SCRIPT}</script>
  <script>{PROGRESS_SCRIPT}</script>
  <script>
    var views = ['dashboard','templates'];
    var titles = {{'dashboard':'Dashboard','templates':'Plan'}};
    function showView(v) {{
      views.forEach(function(x) {{
        document.getElementById('view-' + x).classList.toggle('on', x === v);
      }});
      document.querySelectorAll('.side a,.bmob button').forEach(function(el) {{
        el.classList.toggle('on', el.dataset.view === v);
      }});
      var t = document.getElementById('page-title');
      if (t) t.textContent = titles[v] || 'Log';
    }}
    function closeMenu() {{
      document.querySelector('.side').classList.remove('open');
      document.getElementById('overlay').classList.remove('show');
    }}
    document.getElementById('menu-btn').addEventListener('click', function() {{
      document.querySelector('.side').classList.toggle('open');
      document.getElementById('overlay').classList.toggle('show');
    }});
    document.getElementById('overlay').addEventListener('click', closeMenu);
    document.querySelectorAll('.side a,.bmob button[data-view]').forEach(function(el) {{
      el.addEventListener('click', function(e) {{
        e.preventDefault();
        if (el.dataset.view) showView(el.dataset.view);
        closeMenu();
      }});
    }});
    document.querySelectorAll('.btn[data-go]').forEach(function(b) {{
      b.addEventListener('click', function() {{ showView(b.dataset.go); }});
    }});
    // per-column "View more" (weight training / cardio)
    document.querySelectorAll('.view-more').forEach(function(btn) {{
      btn.addEventListener('click', function() {{
        var col = btn.parentElement;
        var shown = 0;
        col.querySelectorAll('.more-hidden').forEach(function(c) {{
          if (shown < 10) {{ c.classList.remove('more-hidden'); shown++; }}
        }});
        if (!col.querySelector('.more-hidden')) btn.style.display = 'none';
      }});
    }});
    // restore last view
    var last = localStorage.getItem('gr_view');
    if (last && views.indexOf(last) >= 0) showView(last);

    // pull-to-refresh
    var startY = 0, pulling = false;
    var indicator = document.getElementById('ptr-indicator');
    document.addEventListener('touchstart', function(e) {{
      if (window.scrollY === 0) startY = e.touches[0].clientY;
    }}, {{ passive: true }});
    document.addEventListener('touchmove', function(e) {{
      if (window.scrollY === 0 && e.touches[0].clientY - startY > 60) {{ pulling = true; indicator.classList.add('visible'); }}
    }}, {{ passive: true }});
    document.addEventListener('touchend', function() {{
      if (pulling) location.reload();
      pulling = false;
      indicator.classList.remove('visible');
    }});
  </script>
</body>
</html>
"""
    with open(HTML_PATH, "w") as f:
        f.write(html)
    return html


if __name__ == "__main__":
    templates = load_templates()
    entries = load_workouts()
    apply_latest_defaults(templates, entries)
    resolved = [resolve_session(e, templates) for e in entries]
    build_html(resolved, templates, entries)
    print("index.html updated.")
