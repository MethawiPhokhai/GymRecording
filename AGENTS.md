# AGENTS.md

Static personal workout log. Pure Python 3 stdlib — no package manager, no tests, no lint, no typecheck.

## Build

`build.py` (run from repo root) regenerates `index.html` from `templates/*.json` + `workouts/*.json`. Hardcoded relative paths — must run with cwd = repo root.

```sh
python3 build.py
```

`index.html` is a **build artifact**. Do not hand-edit or commit it yourself — CI rewrites it (see below).

## CI

`.github/workflows/update-log.yml` triggers on pushes that change `workouts/**.json`. It runs `build.py`, commits the regenerated `index.html`, and pushes back as `github-actions[bot]`.

Gotchas:
- Editing only a template (`templates/*.json`) or `build.py` does **not** trigger the workflow. Run `build.py` locally and commit `index.html` yourself in that case, or also touch a workout file.
- The workflow does `git pull --rebase` before pushing — avoid pushing `index.html` changes in the same window to prevent races.

## Data model

`templates/*.json` are keyed by the JSON `type` field, not the filename. Known types: `Upper`, `Lower`, `Full body`, `Core`, `Mobility`, `Class`, `Running`. Display order is fixed by `TEMPLATE_ORDER` in `build.py:266`.

`workouts/*.json` filenames follow `YYYY-MM-DD[-suffix].json`. The suffix (e.g. `-upper-web`, `-class-breathwork`) is a human label only — the JSON `type` field is what `build.py` reads. `-web` indicates "logged via the web form", not a distinct type.

Per type:
- **Strength types** (Upper/Lower/Full body/Core/Mobility): `exercises[]` with `weight_kg` xor `weight_lbs`, `sets`, `reps`, `completed`. `resolve_session` (build.py:74) keeps only `completed: true` exercises and merges missing fields from the matching template.
- **Class** (`type: "Class"`): `name` (matches a class in `templates/class.json`) + optional `duration_minutes`. No exercises.
- **Running** (`type: "Running"`): `duration_minutes`, `distance_km`, `pace`, `avg_heart_rate_bpm`, `calories`, `note`. Passed through as-is.

Weights use **mixed units by intent** — kg and lbs both appear across exercises; do not normalize.

`apply_latest_defaults` (build.py:35) overwrites template defaults with the most recently recorded weight per exercise name at build time. Template defaults in the JSON are therefore not canonical and drift as workouts are added.

## Conventions

- Bangkok timezone (UTC+7) is used for the "updated" timestamp in `index.html`.
- Adding a workout = drop a new `workouts/YYYY-MM-DD*.json` and push; CI rebuilds the page.
- Branch naming seen in history: `claude/<topic>-<id>`. Commits like `log: add workout via web`, `chore: update workout log` (the latter is the CI commit message — don't reuse it for manual commits).