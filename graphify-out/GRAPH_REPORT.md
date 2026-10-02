# Graph Report - GymRecording  (2026-10-03)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 61 nodes · 104 edges · 10 communities (6 shown, 4 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `175830d1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- norm_weight_lbs
- build.py
- build_html
- load_all_workouts
- build_progress_card
- main
- record_workout
- build_statgrid
- trend_vs_prev

## God Nodes (most connected - your core abstractions)
1. `main()` - 8 edges
2. `norm_weight_lbs()` - 6 edges
3. `point_from_exercise()` - 6 edges
4. `build_progress_card()` - 6 edges
5. `build_html()` - 5 edges
6. `build_progress_view()` - 5 edges
7. `load_all_workouts()` - 5 edges
8. `progress_summary()` - 5 edges
9. `record_workout()` - 5 edges
10. `trend_vs_prev()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `build_progress_view()` --calls--> `collect_progress()`  [EXTRACTED]
  build.py → build.py  _Bridges community 0 → community 3_
- `merge_exercises()` --calls--> `norm_weight_lbs()`  [EXTRACTED]
  build.py → build.py  _Bridges community 0 → community 2_
- `build_card_html()` --calls--> `format_sets_reps()`  [EXTRACTED]
  build.py → build.py  _Bridges community 3 → community 5_
- `build_html()` --calls--> `build_statgrid()`  [EXTRACTED]
  build.py → build.py  _Bridges community 3 → community 8_
- `build_progress_view()` --calls--> `trend_vs_prev()`  [EXTRACTED]
  build.py → build.py  _Bridges community 3 → community 9_

## Import Cycles
- None detected.

## Communities (10 total, 4 thin omitted)

### Community 0 - "norm_weight_lbs"
Cohesion: 0.20
Nodes (6): apply_latest_defaults(), collect_progress(), display_weight(), norm_weight_lbs(), point_from_exercise(), _reps_from_note()

### Community 3 - "build_html"
Cohesion: 0.33
Nodes (6): build_card_html(), build_html(), col(), build_progress_view(), build_template_section(), group_tag()

### Community 4 - "load_all_workouts"
Cohesion: 0.40
Nodes (6): calc_volume(), fmt_weight(), full_summary(), load_all_workouts(), normalize_name(), progress_summary()

### Community 5 - "build_progress_card"
Cohesion: 0.40
Nodes (4): build_progress_card(), build_sparkline(), format_sets_reps(), format_volume()

### Community 6 - "main"
Cohesion: 0.40
Nodes (4): cardio_summary(), main(), push_to_github(), record_running()

### Community 7 - "record_workout"
Cohesion: 0.50
Nodes (4): list_template(), load_template(), parse_exercise_data(), record_workout()

## Knowledge Gaps
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `point_from_exercise()` connect `norm_weight_lbs` to `build.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `norm_weight_lbs()` connect `norm_weight_lbs` to `build.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `collect_progress()` connect `norm_weight_lbs` to `build.py`, `build_html`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._