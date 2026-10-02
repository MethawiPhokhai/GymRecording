# Graph Report - GymRecording  (2026-10-02)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 27 nodes · 40 edges · 6 communities (3 shown, 3 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `41cec495`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- build.py
- build_progress_card
- point_from_exercise
- build_html
- build_progress_view
- apply_latest_defaults

## God Nodes (most connected - your core abstractions)
1. `build_progress_card()` - 5 edges
2. `trend_vs_prev()` - 5 edges
3. `point_from_exercise()` - 5 edges
4. `build_progress_view()` - 5 edges
5. `build_html()` - 4 edges
6. `collect_progress()` - 4 edges
7. `merge_exercises()` - 2 edges
8. `resolve_session()` - 2 edges
9. `build_sparkline()` - 2 edges
10. `_cmp()` - 2 edges

## Surprising Connections (you probably didn't know these)
- `build_progress_view()` --calls--> `build_progress_card()`  [EXTRACTED]
  build.py → build.py  _Bridges community 1 → community 4_
- `collect_progress()` --calls--> `point_from_exercise()`  [EXTRACTED]
  build.py → build.py  _Bridges community 2 → community 4_
- `build_html()` --calls--> `build_progress_view()`  [EXTRACTED]
  build.py → build.py  _Bridges community 3 → community 4_

## Import Cycles
- None detected.

## Communities (6 total, 3 thin omitted)

### Community 1 - "build_progress_card"
Cohesion: 0.33
Nodes (5): build_progress_card(), build_sparkline(), _cmp(), format_volume(), trend_vs_prev()

### Community 2 - "point_from_exercise"
Cohesion: 0.50
Nodes (3): display_weight(), norm_weight_kg(), point_from_exercise()

### Community 3 - "build_html"
Cohesion: 0.67
Nodes (3): build_card_html(), build_html(), build_template_section()

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `point_from_exercise()` connect `point_from_exercise` to `build.py`, `build_progress_view`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `trend_vs_prev()` connect `build_progress_card` to `build.py`, `build_progress_view`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Why does `collect_progress()` connect `build_progress_view` to `build.py`, `point_from_exercise`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._