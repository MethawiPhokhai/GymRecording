#!/usr/bin/env python3
import html
import json
import os
import re
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
    """Template defaults follow the MOST RECENT logged weight — not the all-time max.

    Deliberate: a deliberate back-off (deload, niggle, form reset) must not be undone
    by the app resurrecting an old peak as the suggested load.
    """
    latest = {}
    for entry in sorted(all_entries, key=lambda e: e.get("date", "")):
        for ex in entry.get("exercises", []):
            w = norm_weight_lbs(ex)
            if w is not None:
                latest[ex["name"]] = w
    for t in templates.values():
        for e in t.get("exercises", []):
            if e["name"] in latest:
                e["default_weight_lbs"] = round(latest[e["name"]] * 2) / 2


def merge_exercises(session_exercises, template):
    if not template:
        return session_exercises
    pool = {e["name"]: e for e in template.get("exercises", [])}
    merged = []
    for ex in session_exercises:
        name = ex["name"]
        base = pool.get(name, {})
        weight_lbs = norm_weight_lbs(ex)
        if weight_lbs is None:
            weight_lbs = base.get("default_weight_lbs")
        merged.append({
            "name":        name,
            "group":       base.get("group", ""),
            "weight_lbs":  weight_lbs,
            "sets":        ex.get("sets")        or base.get("default_sets"),
            "reps":        ex.get("reps")        or base.get("default_reps"),
            "reps_by_set": ex.get("reps_by_set") or None,
            "completed":   ex.get("completed", False),
            "note":        ex.get("note", ""),
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

    if workout_type in ("Running", "Cycling"):
        return entry

    exercises = [e for e in entry.get("exercises", []) if e.get("completed")]
    merged = merge_exercises(exercises, template)
    return {**entry, "exercises": merged}


TYPE_COLORS = {
    "Upper":     "#4f8ef7",
    "Push A":    "#4f8ef7",
    "Pull B":    "#7bb0ff",
    "Lower":     "#f7934f",
    "Lower A":   "#f7934f",
    "Lower B":   "#ffab5c",
    "Calf & Ankle": "#ffc46b",
    "Full body": "#e3c04f",
    "Core":     "#f75f8f",
    "Mobility": "#4fd8f7",
    "Class":    "#a04ff7",
    "Running":  "#4ff7a0",
    "Cycling":  "#33c3f0",
    "Hip Flexor": "#e39d4f",
    "Long Sitting": "#8f7dff",
}
TYPE_DEFAULT = "#888"


def group_tag(group):
    """Small grey muscle-group label shown after an exercise name, e.g. '(Chest)'."""
    if not group:
        return ""
    return f" <span class='grp'>({group})</span>"


def build_card_html(entry):
    date = entry.get("date", "-")
    day = entry.get("day", "-")
    workout_type = entry.get("type", "-")
    color = TYPE_COLORS.get(workout_type, TYPE_DEFAULT)

    if workout_type in ("Running", "Cycling"):
        duration = entry.get("duration_minutes")
        distance = entry.get("distance_km")
        pace = entry.get("pace")
        hr = entry.get("avg_heart_rate_bpm")
        calories = entry.get("calories")
        note = entry.get("note", "")
        parts = []
        if duration:
            h, m = divmod(int(round(duration)), 60)
            parts.append(f"{h}h {m}min" if h else f"{m} min")
        if distance:  parts.append(f"{distance} km")
        if pace:      parts.append(f"pace {pace}")
        summary_str = " · ".join(parts)
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
      <span class="count">{summary_str}</span>
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
        weight = wspan(e.get("weight_lbs"))
        rows += (
            f"<tr>"
            f"<td>{e['name']}{group_tag(e.get('group'))}</td>"
            f"<td>{weight}</td>"
            f"<td>{format_sets_reps(e.get('sets'), e.get('reps'), e.get('reps_by_set'))}</td>"
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
    return wspan(ex.get("default_weight_lbs"))


CHECK_SVG = ("<svg width='14' height='14' viewBox='0 0 16 16' aria-hidden='true'><path d='M3.5 8.5l3 3 6-7' "
             "fill='none' stroke='#06240f' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'/></svg>")
CARDIO_TYPES = ("Class", "Running", "Cycling")


def plan_row_html(name, group, also):
    """One compact Plan row. The hidden .w-num/.sr-sets/.sr-reps inputs are the source of
    truth read by rowData(); the value chip + bottom sheet are just a nicer editor for them."""
    nm = html.escape(name, quote=True)
    sub = html.escape(group or "")
    if also:
        names = html.escape(", ".join(also))
        sub += (" · " if sub else "") + f"<span class='also-off'>also in {names}</span><em class='also-on'>also ticks in {names}</em>"
    return (
        f"<div class='sel-row prow' data-name='{nm}' data-group='{html.escape(group or '', quote=True)}' "
        f"data-also='{html.escape(', '.join(also), quote=True)}'>"
        f"<label class='ck'><input type='checkbox' class='sel' aria-label='Tick {nm}'><span>{CHECK_SVG}</span></label>"
        f"<div class='nm exname' data-name='{nm}'><b>{html.escape(name)}</b><span class='nsub'>{sub}</span></div>"
        f"<button type='button' class='val' aria-label='Edit weight, sets and reps'></button>"
        f"%INPUTS%</div>\n"
    )


def plan_inputs_html(num, sets, reps):
    return (f"<input type='number' class='w-num' step='0.5' value='{num}' data-lbs='{num}' hidden>"
            f"<input type='number' class='sr-sets' value='{sets}' hidden>"
            f"<input type='text' class='sr-reps' value='{reps}' hidden>")


def build_template_section(template, also=None):
    """Plan section for one template. `also` maps exercise name -> other routine types it appears in."""
    also = also or {}
    workout_type = template.get("type", "-")
    color = TYPE_COLORS.get(workout_type, TYPE_DEFAULT)
    wt = html.escape(workout_type, quote=True)
    head = f"<span class='dot'></span><b>{html.escape(workout_type)}</b>"

    if workout_type == "Class":
        chips = "".join(
            f'<span class="chip sel-chip" data-name="{html.escape(c["name"], quote=True)}">{html.escape(c["name"])}'
            f'<small> · <input type="number" class="dur" '
            f'value="{c["default_duration_minutes"]}"> min</small></span>'
            for c in template.get("classes", [])
        )
        return f"""
  <section class="psec" data-type="{wt}" data-color="{color}" style="--c:{color}">
    <div class="psh">{head}</div>
    <div class="chip-row">{chips}</div>
  </section>"""

    if workout_type == "Running":
        return f"""
  <section class="psec" data-type="{wt}" data-color="{color}" style="--c:{color}">
    <div class="psh">{head}</div>
    <label class="run-toggle"><input type="checkbox" class="sel-run"> Log a run today</label>
    <div class="run-grid">
      <label class="run-cell">Duration (min)<input type="number" class="rfield" data-r="duration_minutes" step="1" placeholder="-"></label>
      <label class="run-cell">Distance (km)<input type="number" class="rfield" data-r="distance_km" step="0.01" placeholder="-"></label>
      <label class="run-cell">Pace (min/km)<input type="text" class="rfield" data-r="pace" placeholder="7:04"></label>
      <label class="run-cell">Avg HR (bpm)<input type="number" class="rfield" data-r="avg_heart_rate_bpm" placeholder="-"></label>
      <label class="run-cell">Calories (kcal)<input type="number" class="rfield" data-r="calories" placeholder="-"></label>
      <label class="run-cell run-note">Note<input type="text" class="rfield" data-r="note" placeholder="Zone 2 / location"></label>
    </div>
  </section>"""

    if workout_type == "Cycling":
        return f"""
  <section class="psec" data-type="{wt}" data-color="{color}" style="--c:{color}">
    <div class="psh">{head}</div>
    <label class="run-toggle"><input type="checkbox" class="sel-run"> Log cycling today</label>
    <div class="run-grid">
      <label class="run-cell">Duration (min)<input type="number" class="rfield" data-r="duration_minutes" step="1" placeholder="-"></label>
      <label class="run-cell">Avg HR (bpm)<input type="number" class="rfield" data-r="avg_heart_rate_bpm" placeholder="-"></label>
      <label class="run-cell">Calories (kcal)<input type="number" class="rfield" data-r="calories" placeholder="-"></label>
      <label class="run-cell run-note">Note<input type="text" class="rfield" data-r="note" placeholder="Zone 2 / recovery"></label>
    </div>
  </section>"""

    exercises = template.get("exercises", [])
    if not exercises:
        return ""
    rows = ""
    for e in exercises:
        num = e.get("default_weight_lbs")
        num = f"{num:g}" if num else ""
        sets = e.get("default_sets") or ""
        reps = e.get("default_reps") or ""
        rows += plan_row_html(e["name"], e.get("group"), also.get(e["name"], [])).replace(
            "%INPUTS%", plan_inputs_html(num, sets, html.escape(str(reps), quote=True)))
    return f"""
  <section class="psec" data-type="{wt}" data-color="{color}" style="--c:{color}" id="sec-{re.sub(r'[^a-z0-9]+', '-', workout_type.lower())}">
    <div class="psh">{head}<span class="pcnt">0/{len(exercises)}</span><button type="button" class="ptick">Tick all</button></div>
    <div class="plist" data-type="{wt}">
{rows}    </div>
    <button type="button" class="padd" data-type="{wt}">+ Add exercise</button>
  </section>"""


TEMPLATE_ORDER = ["Push A", "Pull B", "Lower", "Calf & Ankle", "Full body", "Core", "Mobility", "Hip Flexor", "Long Sitting", "Class", "Running", "Cycling"]

LBS_TO_KG = 0.45359237
KG_TO_LBS = 2.20462262

# The log is lbs-only: workouts store `weight_lbs`, templates store
# `default_weight_lbs`; the UI shows one unit at a time (switch in the topbar or
# any row's unit button). `weight_kg` is still READ
# as a fallback so a stray kg value renders correctly instead of vanishing,
# but nothing in this file writes it any more.
UNIT = "lbs"


def wspan(lbs):
    """Read-only weight that follows the page's lbs/kg switch (JS re-renders .wv)."""
    if lbs is None or lbs == "":
        return "-"
    try:
        v = float(lbs)
    except (TypeError, ValueError):
        return str(lbs)
    return f'<span class="wv" data-lbs="{v:g}">{v:g} {UNIT}</span>'


def norm_weight_lbs(ex):
    """Weight in lbs, whichever field the entry happens to carry."""
    if ex.get("weight_lbs"):
        return float(ex["weight_lbs"])
    if ex.get("weight_kg"):
        return round(float(ex["weight_kg"]) * KG_TO_LBS * 2) / 2
    return None


def display_weight(ex):
    v = norm_weight_lbs(ex)
    return "BW" if v is None else wspan(v)


def format_sets_reps(sets, reps, reps_by_set=None):
    """Render "4×12" for a single rep value, or "12/10/10/8" (×4) for a per-set list."""
    if reps_by_set:
        vals = "/".join(str(r) for r in reps_by_set)
        return f"{len(reps_by_set)}× <span class='rbs'>{vals}</span>"
    if sets and reps:
        return f"{sets}×{reps}"
    return "-"


def _reps_from_note(note):
    """Parse a per-set rep string like '12/10/10/8' or '12 10 10 8' → [12,10,10,8]."""
    if not note:
        return None
    vals = [int(s) for s in re.split(r"[\s,/]+", note.strip()) if s.lstrip("-").isdigit()]
    return vals if len(vals) >= 2 else None


def point_from_exercise(date, ex):
    """One measurable data point, or None if the entry has no numbers at all."""
    w = norm_weight_lbs(ex)
    sets, reps = ex.get("sets"), ex.get("reps")
    reps_by_set = ex.get("reps_by_set") or _reps_from_note(ex.get("note"))
    if reps_by_set:
        # Per-set rep list (e.g. [12,10,10,8]) → total work = sum of reps.
        sets = len(reps_by_set)
        reps = sum(reps_by_set)
        work = reps
    else:
        work = sets * reps if (sets and reps) else None
    if w is None and work is None:
        return None
    if w is not None and work:
        volume = w * work
    elif work:
        volume = work  # bodyweight: total reps
    else:
        volume = None
    if ex.get("weight_lbs"):
        unit, raw = UNIT, float(ex["weight_lbs"])
    elif ex.get("weight_kg"):
        unit, raw = UNIT, norm_weight_lbs(ex)
    else:
        unit, raw = None, None
    return {
        "date": date,
        "weight": display_weight(ex),
        "w": w,
        "unit": unit,
        "raw": raw,
        "sets": sets,
        "reps": reps,
        "reps_by_set": reps_by_set,
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
    if prev["w"] is not None and cur["w"] is not None:
        d = _cmp(cur["w"], prev["w"])
        if d:
            if prev["unit"] == cur["unit"]:
                delta = f"{cur['raw'] - prev['raw']:+g} {cur['unit']}"
            else:
                delta = f"{cur['w'] - prev['w']:+.1f} {UNIT}"
            return ("up", f"▲ {delta}") if d > 0 else ("down", f"▼ {delta}")
        d = _cmp(cur["work"], prev["work"])
    elif prev["w"] is None and cur["w"] is not None:
        return "up", "▲ +weight"   # bodyweight → added weight
    elif prev["w"] is not None and cur["w"] is None:
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
    if p["w"] is None:
        return f"{p['volume']:g} reps"
    return f"{p['volume']:g} {UNIT}"


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
        sr = format_sets_reps(p["sets"], p["reps"], p.get("reps_by_set")) if p["work"] else "-"
        rows += (
            f"<tr>"
            f"<td>{p['date']}</td>"
            f"<td>{p['weight']}</td>"
            f"<td>{sr}</td>"
            f"<td>{format_volume(p)}</td>"
            f"<td><span class='trend {d_cls}'>{d_label}</span></td>"
            f"</tr>\n"
        )

    sr_latest = format_sets_reps(latest["sets"], latest["reps"], latest.get("reps_by_set")) if latest["work"] else ""
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
    .w-kg { width: 3.4rem; text-align: center; color: #7d8590; }
    .w-kg:focus { color: #e6edf3; }
    .w-unit2 { opacity: .6; }
    .sr-sets, .sr-reps { width: 3rem; text-align: center; }
    .srcell { white-space: nowrap; }
    .exname input { width: 10rem; }
    .dur { width: 3.6rem; padding: .1rem .3rem; font-size: .8rem; }
    .w-unit {
      background: #0d1117; color: #7d8590; border: 1px solid #30363d;
      border-radius: 6px; padding: .28rem .55rem; font-size: .8rem;
      font-family: inherit; margin-left: .3rem;
      display: inline-block; white-space: nowrap;
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
      const tr = cb.closest('.sel-row');
      const type = tr.closest('[data-type]').dataset.type;
      const nameEl = tr.querySelector('.exname input') || tr.querySelector('.exname');
      let name = (nameEl.value !== undefined ? nameEl.value : (nameEl.dataset.name || nameEl.textContent)).trim();
      // Template rows render the muscle tag as a child span; strip exactly that, so
      // "Chest fly (Chest)" is never logged — apply_latest_defaults and collect_progress
      // both key off the exact name. Only strip the RENDERED tag, never a name that
      // legitimately ends in parentheses (e.g. "* Dead bug (long lever)").
      const grpEl = nameEl.querySelector ? nameEl.querySelector('.grp') : null;
      if (grpEl && name.endsWith(grpEl.textContent)) {
        name = name.slice(0, -grpEl.textContent.length).trim();
      }
      const ex = { name, completed: true };
      const w = parseFloat(tr.querySelector('.w-num').dataset.lbs);
      if (w > 0) ex.weight_lbs = w;   // data-lbs is the canonical stored value
      const sets = parseInt(tr.querySelector('.sr-sets').value);
      const repsRaw = tr.querySelector('.sr-reps').value.trim();
      const reps = parseInt(repsRaw);
      if (sets > 0) ex.sets = sets;
      // Allow per-set reps: "12 10 10 8" (spaces/commas) → reps_by_set array.
      const vals = repsRaw.split(/[\s,]+/).map(s => parseInt(s)).filter(n => !isNaN(n));
      if (vals.length > 1) {
        ex.reps_by_set = vals;
        ex.sets = vals.length;   // keep sets consistent with the list length
      } else if (reps > 0) {
        ex.reps = reps;
      }
      return { kind: 'exercise', type, ex };
    }

    function selections() {
      const items = [];
      // A move that lives in several routines is one shared selection: log it once.
      const seen = new Set();
      document.querySelectorAll('.sel:checked').forEach(cb => {
        const d = rowData(cb);
        if (!d.ex.name || seen.has(d.ex.name)) return;
        seen.add(d.ex.name);
        items.push(d);
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

    // The page now uses one top navigation on every viewport.
    function syncNavHeight() {
      document.documentElement.style.setProperty('--nav-h', '0px');
    }
    syncNavHeight();
    window.addEventListener('resize', syncNavHeight);
    window.addEventListener('orientationchange', () => setTimeout(syncNavHeight, 120));

    const rowsByName = name =>
      Array.from(document.querySelectorAll('.sel-row')).filter(r => r.dataset.name === name);
    const tickedCount = list => list.filter(r => r.querySelector('.sel').checked).length;

    function refreshBar() {
      const items = selections();
      const n = items.length;
      // routines in the mix (colour dots) + cardio
      const mix = [];
      const seenType = new Set();
      items.forEach(i => {
        if (i.kind !== 'exercise' || seenType.has(i.type)) return;
        seenType.add(i.type);
        const sec = document.querySelector('.psec[data-type="' + i.type.replace(/"/g, '\\"') + '"]');
        mix.push('<span><span class="dot" style="--c:' + (sec ? sec.dataset.color : '#888') + '"></span>' + i.type + '</span>');
      });
      const cardioN = items.filter(i => i.kind !== 'exercise').length;
      if (cardioN) mix.push('<span><span class="dot" style="--c:#22d3ee"></span>Cardio</span>');
      savecount.innerHTML = '<b>' + n + ' selected</b><div class="mix">' + mix.join('') + '</div>';
      savebar.classList.toggle('visible', n > 0);

      // per-section counts, chips, tab badges
      let strengthN = 0;
      document.querySelectorAll('.psec').forEach(sec => {
        const rows = Array.from(sec.querySelectorAll('.sel-row'));
        if (!rows.length) return;
        const t = tickedCount(rows);
        strengthN += t;
        sec.querySelector('.pcnt').textContent = t + '/' + rows.length;
        const all = t === rows.length;
        sec.querySelector('.ptick').textContent = all ? 'Clear' : 'Tick all';
        const chip = document.querySelector('.pchip[data-go="' + sec.id + '"] i');
        if (chip) {
          chip.textContent = t || chip.dataset.n;
          chip.classList.toggle('n', t > 0);
        }
      });
      const setBadge = (tab, k) => {
        const i = document.querySelector('.pmode [data-pt="' + tab + '"] i');
        i.textContent = k || '';
        i.style.display = k ? '' : 'none';
      };
      setBadge('s', items.filter(i => i.kind === 'exercise').length);
      setBadge('c', cardioN);
    }

    // Ticking a move ticks it everywhere it appears (one shared selection).
    function onTick(cb) {
      const row = cb.closest('.sel-row');
      row.classList.toggle('on', cb.checked);
      (row.dataset.name ? rowsByName(row.dataset.name) : []).forEach(r => {
        const c = r.querySelector('.sel');
        c.checked = cb.checked;
        r.classList.toggle('on', cb.checked);
      });
      refreshBar();
    }

    function bindRow(row) {
      row.addEventListener('click', e => {
        if (e.target.closest('.ck, .val, input, select, button')) return;
        const cb = row.querySelector('.sel');
        cb.checked = !cb.checked;
        onTick(cb);
      });
      row.querySelector('.sel').addEventListener('change', e => onTick(e.target));
      row.querySelector('.val').addEventListener('click', () => openSheet(row));
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
    document.querySelectorAll('.sel-run').forEach(c => c.addEventListener('change', refreshBar));

    document.querySelectorAll('.ptick').forEach(btn =>
      btn.addEventListener('click', () => {
        const rows = Array.from(btn.closest('.psec').querySelectorAll('.sel-row'));
        const want = tickedCount(rows) !== rows.length;
        rows.forEach(r => { const c = r.querySelector('.sel'); c.checked = want; onTick(c); });
      }));

    function newRowHtml(name) {
      return `
        <label class='ck'><input type='checkbox' class='sel' checked aria-label='Tick'><span><svg width='14' height='14' viewBox='0 0 16 16' aria-hidden='true'><path d='M3.5 8.5l3 3 6-7' fill='none' stroke='#06240f' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'/></svg></span></label>
        <div class='nm exname'><input type='text' placeholder='Exercise name'></div>
        <button type='button' class='val' aria-label='Edit weight, sets and reps'></button>
        <input type='number' class='w-num' step='0.5' data-lbs='' hidden>
        <input type='number' class='sr-sets' value='3' hidden>
        <input type='text' class='sr-reps' value='15' hidden>`;
    }

    document.querySelectorAll('.padd').forEach(btn =>
      btn.addEventListener('click', () => {
        const list = btn.closest('.psec').querySelector('.plist');
        const row = document.createElement('div');
        row.className = 'sel-row prow on';
        row.dataset.name = '';
        row.innerHTML = newRowHtml();
        list.appendChild(row);
        bindRow(row);
        paintUnit();
        row.querySelector('.exname input').focus();
        refreshBar();
      }));

    // ---- Weight unit: ONE field, switch lbs <-> kg in the header ----------
    // The log stays lbs-only (`weight_lbs`). Whatever unit is selected, the
    // single visible number is in that unit, and saving converts back to lbs.
    const LB_PER_KG = 2.20462262;
    const r05 = v => Math.round(v * 2) / 2;
    let UNIT_SEL = (localStorage.getItem('wunit') === 'kg') ? 'kg' : 'lbs';
    const inLbs   = v => UNIT_SEL === 'kg' ? r05(v * LB_PER_KG) : v;
    const fromLbs = v => UNIT_SEL === 'kg' ? r05(v / LB_PER_KG) : v;

    let sheetRow = null;
    const fmtN = v => String(+v.toFixed(1));

    // Value chip text, e.g. "44 lbs · 4×8" or "BW · 3×6".
    function paintVal(row) {
      const lbs = parseFloat(row.querySelector('.w-num').dataset.lbs);
      const w = (!isNaN(lbs) && lbs > 0) ? fmtN(fromLbs(lbs)) + '<small> ' + UNIT_SEL + '</small>' : 'BW';
      const sets = row.querySelector('.sr-sets').value || '-';
      const reps = (row.querySelector('.sr-reps').value.trim().split(/[\\s,]+/).filter(Boolean).join('/')) || '-';
      row.querySelector('.val').innerHTML = w + ' <small>·</small> ' + sets + '×' + reps;
    }

    function paintUnit() {
      document.querySelectorAll('.w-num').forEach(i => {
        const lbs = parseFloat(i.dataset.lbs);
        if (!isNaN(lbs)) i.value = fromLbs(lbs);
      });
      document.querySelectorAll('.sel-row').forEach(paintVal);
      if (sheetRow) paintSheet();
      document.querySelectorAll('.w-tgl').forEach(b =>
        b.classList.toggle('on', b.dataset.u === UNIT_SEL));
      document.querySelectorAll('.wv').forEach(el => {
        const lbs = parseFloat(el.dataset.lbs);
        if (!isNaN(lbs)) el.textContent = fromLbs(lbs) + ' ' + UNIT_SEL;
      });
    }

    function setUnit(u) {
      if (u === UNIT_SEL) return;
      UNIT_SEL = u;
      localStorage.setItem('wunit', u);
      paintUnit();
    }

    // Typing updates the canonical lbs value; switching unit only re-renders from it,
    // so lbs -> kg -> lbs never drifts.
    document.addEventListener('input', e => {
      if (!e.target.classList.contains('w-num')) return;
      const v = parseFloat(e.target.value);
      e.target.dataset.lbs = isNaN(v) ? '' : inLbs(v);
    });
    document.addEventListener('input', e => {
      const nameIn = e.target.closest && e.target.closest('.exname input');
      if (nameIn) nameIn.closest('.sel-row').dataset.name = nameIn.value.trim();
    });

    // ---- Edit sheet (weight / sets / reps) -----------------------------------
    // Edits the row's hidden inputs, so rowData() / the lbs-only log are untouched.
    const psheet = document.getElementById('psheet');
    const pdim = document.getElementById('pdim');
    const stepW = () => UNIT_SEL === 'kg' ? 2.5 : 5;
    const quickW = () => UNIT_SEL === 'kg' ? [1, 2.5, 5] : [2.5, 5, 10];

    const wLbs = row => parseFloat(row.querySelector('.w-num').dataset.lbs);
    const wShown = row => { const l = wLbs(row); return (!isNaN(l) && l > 0) ? fromLbs(l) : null; };
    function setW(row, shown) {
      const inp = row.querySelector('.w-num');
      if (shown == null || shown <= 0) { inp.value = ''; inp.dataset.lbs = ''; }
      else { inp.value = shown; inp.dataset.lbs = inLbs(shown); }
    }
    const repsList = row => row.querySelector('.sr-reps').value.trim().split(/[\\s,]+/)
      .map(x => parseInt(x)).filter(x => !isNaN(x));

    // keep every row of the same move in step with the one being edited
    function syncSame(row) {
      const name = row.dataset.name;
      if (!name) { paintVal(row); return; }
      const qs = ['.w-num', '.sr-sets', '.sr-reps'];
      rowsByName(name).forEach(r => {
        if (r !== row) {
          qs.forEach(q => { r.querySelector(q).value = row.querySelector(q).value; });
          r.querySelector('.w-num').dataset.lbs = row.querySelector('.w-num').dataset.lbs;
        }
        paintVal(r);
      });
    }

    function paintSheet() {
      const row = sheetRow;
      const w = wShown(row);
      document.getElementById('sv-w').innerHTML = w == null ? 'BW' : fmtN(w) + '<small>' + UNIT_SEL + '</small>';
      document.getElementById('sv-s').textContent = row.querySelector('.sr-sets').value || '-';
      document.getElementById('sv-r').textContent = repsList(row).join('/') || '-';
      document.getElementById('sh-quick').innerHTML =
        quickW().map(q => '<button type="button" data-q="' + q + '">+' + q + '</button>').join('') +
        '<button type="button" data-q="bw">BW</button>';
    }

    function openSheet(row) {
      sheetRow = row;
      const nm = row.querySelector('.exname input');
      document.getElementById('sh-title').textContent = nm ? (nm.value || 'New exercise') : row.dataset.name;
      const homes = [row.closest('.psec').dataset.type].concat(row.dataset.also ? row.dataset.also.split(', ') : []);
      document.getElementById('sh-sub').textContent = (row.dataset.group ? row.dataset.group + ' · ' : '') + 'in ' + homes.join(', ');
      paintSheet();
      psheet.classList.add('show');
      pdim.classList.add('show');
    }

    function closeSheet(tick) {
      const row = sheetRow;
      psheet.classList.remove('show');
      pdim.classList.remove('show');
      sheetRow = null;
      if (row && tick) {
        const cb = row.querySelector('.sel');
        cb.checked = true;
        onTick(cb);
      }
    }

    psheet.addEventListener('click', e => {
      const row = sheetRow;
      if (!row) return;
      const st = e.target.closest('[data-st]');
      const q = e.target.closest('[data-q]');
      if (st) {
        const k = st.dataset.st;
        if (k[0] === 'w') {
          const cur = wShown(row);
          const next = k === 'w+' ? (cur || 0) + stepW() : (cur == null ? null : cur - stepW());
          setW(row, next == null ? null : Math.round(next * 100) / 100);
        } else if (k[0] === 's') {
          const v = Math.max(1, (parseInt(row.querySelector('.sr-sets').value) || 3) + (k === 's+' ? 1 : -1));
          row.querySelector('.sr-sets').value = v;
        } else {
          const list = repsList(row);
          const d = k === 'r+' ? 1 : -1;
          row.querySelector('.sr-reps').value = (list.length ? list : [12]).map(x => Math.max(1, x + d)).join(' ');
        }
      } else if (q) {
        if (q.dataset.q === 'bw') setW(row, null);
        else setW(row, Math.round(((wShown(row) || 0) + parseFloat(q.dataset.q)) * 100) / 100);
      } else return;
      syncSame(row);
      paintSheet();
    });
    pdim.addEventListener('click', () => closeSheet(false));
    document.getElementById('sh-done').addEventListener('click', () => closeSheet(true));
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && sheetRow) closeSheet(false); });

    // ---- Plan page chrome: tabs, routine chips, sticky offsets, toast --------
    const planHead = document.getElementById('plan-head');
    function measurePlan() {
      if (planHead && planHead.offsetParent) {
        document.documentElement.style.setProperty('--plan-head-h', planHead.offsetHeight + 'px');
      }
    }
    window.measurePlan = measurePlan;
    window.addEventListener('resize', measurePlan);

    document.querySelectorAll('.pmode button').forEach(b =>
      b.addEventListener('click', () => {
        document.querySelectorAll('.pmode button').forEach(x => x.classList.toggle('on', x === b));
        document.getElementById('pt-s').classList.toggle('on', b.dataset.pt === 's');
        document.getElementById('pt-c').classList.toggle('on', b.dataset.pt === 'c');
        document.getElementById('pchips').style.display = b.dataset.pt === 's' ? '' : 'none';
        window.scrollTo(0, 0);
        measurePlan();
      }));

    const chipEls = Array.from(document.querySelectorAll('.pchip'));
    chipEls.forEach(c => c.addEventListener('click', () => {
      const sec = document.getElementById(c.dataset.go);
      if (!sec) return;
      const top = sec.getBoundingClientRect().top + window.scrollY - planHead.offsetHeight + 1;
      window.scrollTo({ top, behavior: 'smooth' });
    }));

    function spy() {
      if (!planHead || !planHead.offsetParent || !chipEls.length) return;
      const line = planHead.getBoundingClientRect().bottom + 8;
      let cur = chipEls[0].dataset.go;
      chipEls.forEach(c => {
        const sec = document.getElementById(c.dataset.go);
        if (sec && sec.getBoundingClientRect().top <= line) cur = c.dataset.go;
      });
      chipEls.forEach(c => {
        const on = c.dataset.go === cur;
        if (c.classList.contains('on') !== on) {
          c.classList.toggle('on', on);
          if (on) c.parentElement.scrollTo({ left: Math.max(0, c.offsetLeft - 12), behavior: 'smooth' });
        }
      });
    }
    window.addEventListener('scroll', spy, { passive: true });

    let toastTimer;
    function toast(msg) {
      const t = document.getElementById('ptoast');
      t.textContent = msg;
      t.classList.add('show');
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => t.classList.remove('show'), 2400);
    }

    paintUnit();
    refreshBar();
    document.querySelectorAll('.w-tgl').forEach(b =>
      b.addEventListener('click', () => setUnit(b.dataset.u)));

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

        document.querySelectorAll('.sel:checked').forEach(cb => { cb.checked = false; cb.closest('.sel-row').classList.remove('on'); });
        document.querySelectorAll('.sel-chip.selected').forEach(ch => ch.classList.remove('selected'));
        const runClear = document.querySelector('.sel-run');
        if (runClear) runClear.checked = false;
        document.querySelectorAll('.rfield').forEach(f => f.value = '');
        refreshBar();
        toast('Workout saved \u2713 \u00b7 site rebuilds in ~1 min');
      } catch (err) {
        if (String(err).includes('401') || String(err).includes('403')) {
          alert('Token invalid or expired — tap ⚙ to set a new one.');
        } else {
          alert('Save failed: ' + err.message);
        }
      } finally {
        savebtn.disabled = false;
        savebtn.textContent = 'Save';
      }
    });
"""


PAGE_SIZE = 10

#!/usr/bin/env python3
# New tail for build.py — replaces build_html with a Design-3 (Linear-style) dashboard,
# keeping all data functions + SAVE_SCRIPT + PROGRESS_SCRIPT intact.

from datetime import date as _date, timedelta


STRENGTH_TYPES = {"Upper", "Push A", "Pull B", "Lower", "Lower A", "Lower B", "Calf & Ankle", "Full body", "Core", "Mobility", "Hip Flexor", "Long Sitting"}


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

    # Weekly run distance: Monday of the current week → today
    today = datetime.now(BKK).date()
    monday = today - timedelta(days=today.weekday())
    run_week = sum(
        (e.get("distance_km") or 0) for e in raw_entries
        if e.get("type") == "Running" and e.get("date")
        and monday.isoformat() <= e["date"] <= today.isoformat()
    )

    return {
        "last30": sessions,
        "weight": weight,
        "cardio": cardio,
        "distance": distance,
        "run_week": round(run_week, 1),
        "total": total_sessions,
    }


def build_focus_statgrid(entries, raw_entries, templates, focus):
    s = compute_summary(entries, raw_entries)
    history_count = len(collect_progress(raw_entries, templates))
    if focus == "weight":
        stats = [
            ("Last 30 days", s["last30"], "total sessions"),
            ("Weight training", s["weight"], "sessions · 30d"),
            ("Exercises tracked", history_count, "with progress data"),
            ("All-time sessions", s["total"], "in your log"),
        ]
    else:
        stats = [
            ("Cardio sessions", s["cardio"], "last 30 days"),
            ("Distance", f"{s['distance']:.1f}\u00a0km", "last 30 days"),
            ("This week", f"{s['run_week']:.1f}\u00a0km", "Mon → today"),
            ("All-time sessions", s["total"], "in your log"),
        ]
    cards = "".join(
        f'<div class="stat"><div class="k">{label}</div><div class="v">{value}</div><div class="d">{detail}</div></div>'
        for label, value, detail in stats
    )
    return f'<div class="statgrid focus-stats">{cards}</div>'


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

  /* ---- Main ---- */
  .main{width:100%;max-width:1500px;margin:0 auto;padding:18px 18px 40px}
  .view{display:none}
  .view.on{display:block}
  .topbar{display:flex;align-items:center;justify-content:space-between;gap:20px;padding-bottom:24px}
  .topbar h1{font-size:17px;font-weight:700;letter-spacing:-.02em;margin:0}
  .topbar .meta{font-size:12px;color:var(--mut);margin-top:2px}
  .topbar .actions{display:flex;gap:8px;margin-left:auto}
  .top-nav{display:flex;align-items:center;gap:4px;white-space:nowrap}
  .top-nav a{color:var(--mut);font-size:12.5px;font-weight:600;padding:8px 11px;border-radius:8px}
  .top-nav a:hover{background:var(--hover);color:var(--ink)}
  .top-nav a.on{background:var(--accent);color:#fff}
  .top-nav a:focus-visible{outline:2px solid var(--accent2);outline-offset:2px}
  .page-intro{margin-bottom:18px}
  .page-intro h2{font-size:20px;letter-spacing:-.025em;margin:0 0 4px}
  .page-intro p{font-size:13px;color:var(--mut);max-width:52rem}
  .focus-section{margin-top:24px}

  .statgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
  .focus-stats{grid-template-columns:repeat(4,1fr);margin-bottom:24px}
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
  .count{font-size:12.5px;color:var(--mut);text-align:right;font-variant-numeric:tabular-nums;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
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
  .unit-switch{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden;flex-shrink:0}
  .unit-switch button{background:var(--panel2);border:0;color:var(--mut);font:inherit;font-size:12.5px;padding:9px 12px;cursor:pointer;line-height:1}
  .unit-switch button+button{border-left:1px solid var(--line)}
  .unit-switch button.on{background:var(--accent);color:#fff}
  .wv{font-variant-numeric:tabular-nums}
  .rbs{color:var(--accent2);font-family:var(--mono)}
  .exname input{width:9rem}
  .grp{font-size:10px;font-weight:600;opacity:.55;white-space:nowrap;margin-left:.3rem}
  .dur{width:3.4rem;padding:4px 6px;font-size:12px}
  .w-unit:hover{border-color:var(--accent);color:var(--ink)}
  .w-unit:active{background:var(--accent);color:#fff}
  input[type=number]{appearance:textfield;-moz-appearance:textfield}
  input[type=number]::-webkit-inner-spin-button{-webkit-appearance:none}
  .addrow:hover{border-color:var(--accent);color:var(--ink)}
  .run-toggle{display:flex;align-items:center;gap:8px;margin-top:8px;font-size:13px;color:var(--ink);cursor:pointer}
  .run-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:8px}
  .run-cell{display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--mut)}
  .run-note{grid-column:1 / -1}
  .note-row{display:flex;gap:8px;align-items:center;font-size:11px;color:var(--mut)}

  /* ---- Plan page (Claude Design A · one compact list) ---- */
  .sel-run{width:1.1rem;height:1.1rem;accent-color:var(--accent);cursor:pointer;vertical-align:middle}
  .plan{--p-bg:#0c0c0e;--p-sf:#141417;--p-sf2:#1b1b1f;--p-bd:#26262b;--p-div:#1c1c21;--p-tx:#ececf0;--p-mu:#8d8d97;
    --p-ac:#6366f1;--p-ln:#a5a6ff;--p-ok:#22c55e;--p-okt:#06240f;--p-oks:#7dd3a0;--p-ck:#3a3a42;
    max-width:640px;margin:0 auto;font-variant-numeric:tabular-nums}
  .plan button{font:inherit;color:inherit;-webkit-tap-highlight-color:transparent}
  .plan-head{position:sticky;top:0;z-index:20;background:rgba(8,9,12,.96);backdrop-filter:blur(10px);margin:0 -18px;padding:0 18px;border-bottom:1px solid var(--p-bd)}
  .plan-hd{display:flex;justify-content:space-between;align-items:center;padding:10px 0}
  .plan-hd h2{font-size:24px;font-weight:700;letter-spacing:-.02em}
  .plan-hd small{display:block;font-size:12px;color:var(--p-mu);margin-top:2px}
  .plan .unit-switch,.psheet .unit-switch,#psheet .unit-switch{background:var(--p-sf2,#1b1b1f);border:1px solid #26262b;border-radius:10px;padding:2px;overflow:visible}
  .plan .unit-switch button,#psheet .unit-switch button{padding:8px 13px;border-radius:8px;font-size:13px;color:var(--mut);min-height:36px}
  .plan .unit-switch button+button,#psheet .unit-switch button+button{border-left:0}
  .plan .unit-switch button.on,#psheet .unit-switch button.on{background:#6366f1;color:#fff}
  .pmode{display:flex;background:var(--p-sf);border:1px solid var(--p-bd);border-radius:12px;padding:3px;margin-bottom:10px}
  .pmode button{flex:1;min-height:40px;border-radius:9px;font-size:14px;color:var(--p-mu);display:flex;justify-content:center;align-items:center;gap:6px}
  .pmode button.on{background:var(--p-sf2);color:var(--p-tx);box-shadow:0 0 0 1px var(--p-bd)}
  .pmode i{font-style:normal;font-size:11px;font-weight:700;background:var(--p-ok);color:var(--p-okt);border-radius:9px;padding:1px 6px}
  .pmode i:empty{display:none}
  .pchips{display:flex;gap:6px;overflow-x:auto;padding:0 0 10px;scrollbar-width:none}
  .pchips::-webkit-scrollbar{display:none}
  .pchip{flex:none;display:flex;align-items:center;gap:6px;padding:7px 12px;min-height:36px;border-radius:999px;border:1px solid var(--p-bd);background:var(--p-sf);font-size:13px;color:var(--p-mu)}
  .pchip.on{color:var(--p-tx);border-color:var(--c)}
  .pchip i{font-style:normal;font-size:11px}
  .pchip i.n{background:var(--p-ok);color:var(--p-okt);border-radius:8px;padding:0 5px;font-weight:700}
  .dot{flex:none;width:8px;height:8px;border-radius:50%;background:var(--c)}
  .ptab{display:none}
  .ptab.on{display:block}
  .psec{padding-bottom:6px}
  .psh{position:sticky;top:var(--plan-head-h,120px);z-index:10;display:flex;align-items:center;gap:8px;padding:10px 6px 8px;background:rgba(8,9,12,.94);backdrop-filter:blur(8px)}
  .psh b{font-size:14px}
  .pcnt{font-size:12px;color:var(--p-mu)}
  .ptick{margin-left:auto;font-size:13px;color:var(--p-ln);padding:10px 0 10px 12px}
  .prow{display:flex;align-items:center;gap:10px;margin:0 4px;padding:0 6px 0 8px;min-height:52px;border-radius:12px;cursor:pointer}
  .prow+.prow{border-top:1px solid var(--p-div)}
  .prow.on{background:rgba(34,197,94,.08)}
  .prow.on+.prow,.prow+.prow.on{border-top-color:transparent}
  .ck{flex:none;width:44px;height:44px;margin-left:-8px;display:grid;place-items:center;position:relative;cursor:pointer}
  .ck .sel{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;margin:0}
  .ck span{width:24px;height:24px;border-radius:50%;border:2px solid var(--p-ck);display:grid;place-items:center;transition:all .15s;pointer-events:none}
  .ck svg{opacity:0}
  .prow.on .ck span{background:var(--p-ok);border-color:var(--p-ok)}
  .prow.on .ck svg{opacity:1}
  .ck .sel:focus-visible+span{outline:2px solid var(--accent2);outline-offset:2px}
  .prow .nm{flex:1;min-width:0;padding:8px 0;display:flex;flex-direction:column;gap:1px}
  .prow .nm b{font-weight:500;font-size:14.5px;line-height:1.25}
  .nsub{font-size:11.5px;color:var(--p-mu)}
  .nsub em{font-style:normal;color:var(--p-oks)}
  .also-on{display:none}
  .prow.on .also-on{display:inline}
  .prow.on .also-off{display:none}
  .prow .exname input{width:100%;min-height:36px;font-size:14px}
  .val{flex:none;min-height:40px;min-width:96px;padding:8px 10px;border-radius:9px;background:var(--p-sf2);border:1px solid var(--p-bd);font-size:13px;text-align:right;white-space:nowrap}
  .val small{color:var(--p-mu);font-size:inherit}
  .padd{display:block;width:calc(100% - 8px);margin:6px 4px 4px;padding:12px;border:1px dashed var(--p-bd);border-radius:14px;color:var(--p-mu);font-size:14px}
  .plan .chip-row{padding:0 6px}
  .plan .run-toggle,.plan .run-grid{margin-left:6px;margin-right:6px}
  .plan .rfield,.plan .dur{min-height:40px}
  .plan .dur{min-height:0}
  #savebar{left:12px;right:12px;bottom:calc(22px + env(safe-area-inset-bottom));display:flex;max-width:616px;margin:0 auto;padding:10px 10px 10px 16px;gap:10px;justify-content:flex-start;background:#1d1d22;border:1px solid #26262b;border-radius:18px;box-shadow:0 10px 40px rgba(0,0,0,.6);transform:translateY(160%);pointer-events:none;transition:transform .25s cubic-bezier(.3,1.3,.5,1)}
  #savebar.visible{transform:none;pointer-events:auto}
  #savecount{flex:1;min-width:0;font-size:12px;color:var(--mut);display:flex;flex-direction:column;gap:3px}
  #savecount b{color:var(--ink);font-size:15px}
  .mix{display:flex;gap:4px 10px;flex-wrap:wrap}
  .mix>span{display:flex;align-items:center;gap:4px}
  #savebtn{min-height:48px;padding:13px 20px;border-radius:12px;font-size:15px;font-weight:600;background:#6366f1}
  #tokenbtn{min-height:44px;min-width:44px}
  #ptoast{position:fixed;left:50%;top:20px;z-index:60;transform:translate(-50%,-30px);opacity:0;background:#22c55e;color:#06240f;padding:10px 16px;border-radius:999px;font-size:14px;font-weight:600;transition:all .25s;pointer-events:none;white-space:nowrap}
  #ptoast.show{opacity:1;transform:translate(-50%,0)}
  #pdim{position:fixed;inset:0;z-index:70;background:rgba(0,0,0,.55);opacity:0;pointer-events:none;transition:opacity .2s}
  #pdim.show{opacity:1;pointer-events:auto}
  #psheet{position:fixed;left:0;right:0;bottom:0;z-index:71;max-width:640px;margin:0 auto;max-height:92vh;overflow-y:auto;background:#17171b;border-top:1px solid #26262b;border-radius:24px 24px 0 0;padding:10px 18px calc(28px + env(safe-area-inset-bottom));transform:translateY(105%);visibility:hidden;transition:transform .28s cubic-bezier(.2,.9,.3,1),visibility 0s .28s}
  #psheet.show{transform:none;visibility:visible;transition:transform .28s cubic-bezier(.2,.9,.3,1)}
  #psheet .grab{width:40px;height:5px;border-radius:3px;background:#3a3a42;margin:0 auto 14px}
  #psheet h3{font-size:19px}
  #psheet p{margin:2px 0 14px;font-size:13px;color:var(--mut)}
  #psheet .st{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-top:1px solid #26262b}
  #psheet .st>span{font-size:13px;color:var(--mut);width:70px}
  #psheet .stc{display:flex;align-items:center;gap:8px}
  #psheet .sbtn{width:48px;height:48px;border-radius:12px;background:#1b1b1f;border:1px solid #26262b;font-size:22px;display:grid;place-items:center}
  #psheet .sv{min-width:96px;text-align:center;font-size:26px;font-weight:600;font-variant-numeric:tabular-nums}
  #psheet .sv small{font-size:13px;color:var(--mut);font-weight:400;margin-left:3px}
  #psheet .quick{display:flex;gap:6px;padding:0 0 10px 70px}
  #psheet .quick button{flex:1;min-height:40px;border-radius:9px;border:1px solid #26262b;font-size:13px;color:var(--mut)}
  .pbtn{width:100%;margin-top:14px;min-height:48px;padding:13px 20px;border-radius:12px;background:#6366f1;color:#fff;font-weight:600;font-size:15px}
  @media(max-width:600px){.plan-head{margin:0 -14px;padding:0 14px}}

  /* ---- Save bar (floating card; look is defined with the Plan styles above) ---- */
  #savebar{position:fixed;align-items:center;z-index:40}
  #savebtn{border:none;color:#fff;font-family:inherit}
  #savebtn:hover{filter:brightness(1.1)}
  #savebtn:disabled{opacity:.5;cursor:wait}
  #tokenbtn{background:var(--panel2);border:1px solid var(--line);color:var(--mut);border-radius:12px;padding:9px 12px}

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
    .main{width:80%;max-width:1500px;padding:22px 28px 40px}
    .statgrid{grid-template-columns:repeat(4,1fr)}
    .stats{grid-template-columns:repeat(3,1fr)}
  }
  @media(max-width:600px){
    .main{padding:16px 14px 28px}
    .topbar{align-items:flex-start;flex-direction:column;gap:14px;padding-bottom:20px}
    .topbar .actions{width:100%;margin-left:0;overflow-x:auto;padding:2px}
    .top-nav{width:max-content}
    .top-nav a{padding:8px 10px}
    .page-intro h2{font-size:18px}
    .focus-stats{grid-template-columns:1fr 1fr;margin-bottom:20px}
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
    # name -> other routines it also appears in (drives "also in …" and the global tick)
    homes = {}
    for t in ordered:
        for e in t.get("exercises", []):
            homes.setdefault(e["name"], []).append(t["type"])
    also_for = lambda typ: {n: [x for x in ts if x != typ] for n, ts in homes.items() if typ in ts and len(ts) > 1}
    sections = [(t, build_template_section(t, also_for(t["type"]))) for t in ordered]
    strength_secs = [(t, h) for t, h in sections if h and t.get("exercises")]
    cardio_secs = [(t, h) for t, h in sections if h and t["type"] in CARDIO_TYPES]
    strength_html = "\n".join(h for _, h in strength_secs)
    cardio_html = "\n".join(h for _, h in cardio_secs)
    plan_chips = "".join(
        f'<button type="button" class="pchip" data-go="sec-{re.sub(r"[^a-z0-9]+", "-", t["type"].lower())}" '
        f'style="--c:{TYPE_COLORS.get(t["type"], TYPE_DEFAULT)}"><span class="dot"></span>{t["type"]}'
        f'<i data-n="{len(t["exercises"])}">{len(t["exercises"])}</i></button>'
        for t, _ in strength_secs
    )
    latest_date = entries[0].get("date", "—") if entries else "—"
    try:
        _d = datetime.strptime(latest_date, "%Y-%m-%d")
        latest_label = f"{_d.strftime('%b')} {_d.day}"
    except ValueError:
        latest_label = latest_date
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
    <div class="main">
      <div class="topbar">
        <div><h1 id="page-title">Weight Training</h1><div class="meta">latest session {latest_date} · {n} workouts</div></div>
        <div class="actions">
          <div class="unit-switch" id="unitsw" role="group" aria-label="Weight unit">
            <button type="button" class="w-tgl on" data-u="lbs">lbs</button>
            <button type="button" class="w-tgl" data-u="kg">kg</button>
          </div>
          <nav class="top-nav" aria-label="Primary navigation">
            <a class="on" data-view="weight" href="#weight">Weight Training</a>
            <a data-view="cardio" href="#cardio">Cardio</a>
            <a data-view="templates" href="#plan">Plan</a>
          </nav>
        </div>
      </div>

      <div id="view-weight" class="view on">
        <div class="page-intro"><h2>Weight Training</h2><p>Strength sessions, exercise progress, and recent training logs.</p></div>
        {build_focus_statgrid(entries, raw_entries, templates, "weight")}
        <section class="focus-section"><div class="section-title">Progress</div>{progress_view}</section>
        <section class="focus-section"><div class="section-title">Recent sessions</div>{weight_cards}{weight_more}</section>
      </div>

      <div id="view-cardio" class="view">
        <div class="page-intro"><h2>Cardio</h2><p>Running and other cardio sessions, with distance and weekly momentum at a glance.</p></div>
        {build_focus_statgrid(entries, raw_entries, templates, "cardio")}
        <section class="focus-section"><div class="section-title">Recent sessions</div>{cardio_cards}{cardio_more}</section>
      </div>

      <div id="view-templates" class="view">
        <div class="plan">
          <div class="plan-head" id="plan-head">
            <div class="plan-hd">
              <div><h2>Plan</h2><small>last session {latest_label} · {n} workouts</small></div>
              <div class="unit-switch" role="group" aria-label="Weight unit">
                <button type="button" class="w-tgl on" data-u="lbs">lbs</button>
                <button type="button" class="w-tgl" data-u="kg">kg</button>
              </div>
            </div>
            <div class="pmode" role="tablist">
              <button type="button" class="on" data-pt="s">Strength<i></i></button>
              <button type="button" data-pt="c">Cardio<i></i></button>
            </div>
            <div class="pchips" id="pchips">{plan_chips}</div>
          </div>
          <div id="pt-s" class="ptab on">
{strength_html}
          </div>
          <div id="pt-c" class="ptab">
{cardio_html}
          </div>
        </div>
        <div style="height:9rem"></div>
      </div>

      <footer>Updated {updated}</footer>
    </div>
  </div>

  <div id="savebar">
    <div id="savecount"></div>
    <button id="tokenbtn" title="Set GitHub token">⚙</button>
    <button id="savebtn">Save</button>
  </div>
  <div id="ptoast" role="status"></div>
  <div id="pdim"></div>
  <div id="psheet" role="dialog" aria-modal="true" aria-labelledby="sh-title">
    <div class="grab"></div>
    <h3 id="sh-title"></h3>
    <p id="sh-sub"></p>
    <div class="st"><span>Weight</span>
      <div class="stc"><button type="button" class="sbtn" data-st="w-" aria-label="Less weight">&minus;</button><div class="sv" id="sv-w"></div><button type="button" class="sbtn" data-st="w+" aria-label="More weight">+</button></div></div>
    <div class="quick" id="sh-quick"></div>
    <div class="st"><span>Sets</span>
      <div class="stc"><button type="button" class="sbtn" data-st="s-" aria-label="Fewer sets">&minus;</button><div class="sv" id="sv-s"></div><button type="button" class="sbtn" data-st="s+" aria-label="More sets">+</button></div></div>
    <div class="st"><span>Reps</span>
      <div class="stc"><button type="button" class="sbtn" data-st="r-" aria-label="Fewer reps">&minus;</button><div class="sv" id="sv-r"></div><button type="button" class="sbtn" data-st="r+" aria-label="More reps">+</button></div></div>
    <div class="st sh-unit"><span>Unit</span>
      <div class="unit-switch" role="group" aria-label="Weight unit"><button type="button" class="w-tgl on" data-u="lbs">lbs</button><button type="button" class="w-tgl" data-u="kg">kg</button></div></div>
    <button type="button" class="pbtn" id="sh-done">Done</button>
  </div>

  <script>{SAVE_SCRIPT}</script>
  <script>{PROGRESS_SCRIPT}</script>
  <script>
    var views = ['weight','cardio','templates'];
    var titles = {{'weight':'Weight Training','cardio':'Cardio','templates':'Plan'}};
    function showView(v) {{
      views.forEach(function(x) {{
        document.getElementById('view-' + x).classList.toggle('on', x === v);
      }});
      document.querySelectorAll('.top-nav a').forEach(function(el) {{
        el.classList.toggle('on', el.dataset.view === v);
      }});
      var t = document.getElementById('page-title');
      if (t) t.textContent = titles[v] || 'Log';
      var usw = document.getElementById('unitsw');
      if (usw) usw.style.display = (v === 'templates') ? 'none' : '';
      if (window.measurePlan) {{ window.measurePlan(); }}
      history.replaceState(null, '', '#' + v);
    }}
    document.querySelectorAll('.top-nav a').forEach(function(el) {{
      el.addEventListener('click', function(e) {{
        e.preventDefault();
        if (el.dataset.view) showView(el.dataset.view);
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
    var last = location.hash.slice(1);
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
