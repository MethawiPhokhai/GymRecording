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
            "name":       name,
            "weight_lbs": ex.get("weight_lbs") or base.get("default_weight_lbs"),
            "weight_kg":  ex.get("weight_kg"),
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
    <table>
      <thead><tr><th>Exercise</th><th>Weight</th><th>Sets×Reps</th><th>Note</th></tr></thead>
      <tbody>
{rows}      </tbody>
    </table>
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
      <table>
        <thead><tr><th></th><th>Exercise</th><th>Weight</th><th>Sets×Reps</th></tr></thead>
        <tbody data-type="{workout_type}">
{rows}        </tbody>
      </table>
    </div>
    <button class="addrow" data-type="{workout_type}">+ Add exercise</button>
  </div>"""


TEMPLATE_ORDER = ["Upper", "Lower", "Class", "Running"]

SAVE_CSS = """
    .selcell { width: 2.2rem; }
    .sel {
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
    .wcell input, .srcell input, .exname input, .dur {
      background: #0d1117; border: 1px solid #30363d; color: #e6edf3;
      border-radius: 6px; padding: .28rem .4rem;
      font-size: .85rem; font-family: inherit;
    }
    .w-num { width: 4.4rem; }
    .sr-sets, .sr-reps { width: 3rem; text-align: center; }
    .srcell { white-space: nowrap; }
    .exname input { width: 100%; min-width: 8rem; }
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
          const path = `workouts/${date}-${type.toLowerCase()}-web.json`;
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

        document.querySelectorAll('.sel:checked').forEach(cb => cb.checked = false);
        document.querySelectorAll('.sel-chip.selected').forEach(ch => ch.classList.remove('selected'));
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


def build_html(entries, templates):
    cards = "\n".join(build_card_html(e) for e in entries)
    ordered = [templates[t] for t in TEMPLATE_ORDER if t in templates]
    ordered += [t for k, t in templates.items() if k not in TEMPLATE_ORDER]
    template_sections = "\n".join(
        s for s in (build_template_section(t) for t in ordered) if s
    )
    updated = datetime.now(BKK).strftime("%Y-%m-%d %H:%M (Bangkok)")
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
    .tabs {{
      display: flex; gap: .5rem; margin-bottom: 1.25rem;
    }}
    .tab {{
      background: none; border: 1px solid #30363d; color: #7d8590;
      font-size: .85rem; font-weight: 600; font-family: inherit;
      padding: .45rem 1.1rem; border-radius: 20px; cursor: pointer;
      transition: all .15s;
    }}
    .tab.active {{
      background: #1f6feb22; border-color: #1f6feb66; color: #58a6ff;
    }}
    .view {{ display: none; }}
    .view.active {{ display: block; }}
    .tpl-section {{ margin-bottom: 1.5rem; }}
    .tpl-head {{ display: flex; align-items: center; gap: .75rem; }}
    .chip-row {{ display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .6rem; }}
    .chip {{
      background: #161b22; border: 1px solid #30363d;
      border-radius: 20px; padding: .35rem .85rem;
      font-size: .82rem; color: #c9d1d9;
    }}
    .chip small {{ color: #7d8590; }}
    #ptr-indicator {{
      display: flex; align-items: center; justify-content: center;
      height: 0; overflow: hidden; transition: height .2s;
      color: #7d8590; font-size: .8rem; gap: .4rem;
    }}
    #ptr-indicator.visible {{ height: 48px; }}
    #ptr-indicator svg {{ animation: spin 1s linear infinite; }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
{SAVE_CSS}
  </style>
</head>
<body>
  <div id="ptr-indicator">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
    </svg>
    Refreshing…
  </div>
  <div class="container">
    <header>
      <h1>Gym Recording</h1>
      <p>Personal workout log — tracking sets, reps, and weights over time.</p>
    </header>
    <div class="tabs">
      <button class="tab active" data-view="log">Log</button>
      <button class="tab" data-view="templates">Templates</button>
    </div>
    <div id="view-log" class="view active">
      <p class="section-title">Latest 10 Workouts</p>
      {cards}
    </div>
    <div id="view-templates" class="view">
      <p class="section-title">Default Exercises</p>
      {template_sections}
      <div style="height:4.5rem"></div>
    </div>
    <footer>Updated {updated}</footer>
  </div>
  <div id="savebar">
    <span id="savecount"></span>
    <button id="savebtn">Save to Log</button>
    <button id="tokenbtn" title="Set GitHub token">⚙</button>
  </div>
  <script>
{SAVE_SCRIPT}
  </script>
  <script>
    document.querySelectorAll('.tab').forEach(tab => {{
      tab.addEventListener('click', () => {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('view-' + tab.dataset.view).classList.add('active');
      }});
    }});

    let startY = 0, pulling = false;
    const indicator = document.getElementById('ptr-indicator');
    document.addEventListener('touchstart', e => {{
      if (window.scrollY === 0) startY = e.touches[0].clientY;
    }}, {{ passive: true }});
    document.addEventListener('touchmove', e => {{
      if (window.scrollY === 0 && e.touches[0].clientY - startY > 60) {{
        pulling = true;
        indicator.classList.add('visible');
      }}
    }}, {{ passive: true }});
    document.addEventListener('touchend', () => {{
      if (pulling) {{ location.reload(); }}
      pulling = false;
      indicator.classList.remove('visible');
    }});
  </script>
</body>
</html>
"""
    with open(HTML_PATH, "w") as f:
        f.write(html)


if __name__ == "__main__":
    templates = load_templates()
    entries = load_workouts()
    resolved = [resolve_session(e, templates) for e in entries]
    build_html(resolved, templates)
    print("index.html updated.")
