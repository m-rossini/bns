# Bean World — Task Board

Legend: `[x]` done · `[~]` in progress · `[ ]` pending

| # | Task | Branch / worktree | Status |
|---|------|-------------------|--------|
| 1 | Weather-field box: right-hand text overflows the panel | `feat/rendering` | [x] |
| 2 | Eliminate `draw_text` PerformanceWarning via cached `arcade.Text` | `feat/rendering` | [x] |
| 3 | Logging (operational + business), configurable level in config and Makefile (default INFO) | `feat/climate-logging` | [x] |
| 4 | Rewrite `README.md` to match current code (LAST step) | `feat/docs` | [x] |
| 5 | Inspector/pointer misalignment (scaled displays + cell snapping) | `feat/rendering` | [x] |
| 6 | Per-location climate gradients controlled by strategy config (N/S, W/E, centre-out, tuples) | `feat/climate-logging` | [x] |
| 7 | Grid rendering derived from `cell_size` / world cols-rows | `feat/rendering` | [x] |
| 8 | `diagrams.md` with Mermaid class + sequence diagrams, linked from README | `feat/docs` | [x] |
| 9 | Align `spec.md`, `AGENTS.md` and `CLAUDE.md` with the code | `feat/docs` | [x] |
| 10 | Verify: compile, headless run, windowed screenshots, container verify | all | [~] |
| 11 | Commit → push → PR → merge → clean per `skills/git.md` | all | [~] |

## Verification log

- `python3 -m compileall sim` — OK on every branch.
- Headless (`BEAN_HEADLESS=1 BEAN_HEADLESS_FRAMES=11000`) — Spring → Summer
  transition, day/season/weather events emitted.
- Headless DEBUG — `environment.reading`, `weather.front`, `season.palette`
  samples emitted.
- Windowed screenshots (`/tmp/opencode/50_start.png` … `59_end.png`) — no
  PerformanceWarning, weather panel fits, click → `cell (15, 8)` round-trip
  verified.
- Container `make build` — OK.
- Container `make run LOG_LEVEL=DEBUG BEAN_HEADLESS_FRAMES=300` — structured
  logs visible.
- Container `make verify LOG_LEVEL=DEBUG BEAN_HEADLESS_FRAMES=300` — OK.
- Container `DISPLAY=:0 make run-container-ui` — window created,
  `app.start` / `app.window_created` logged.
- Keyboard state machine — SPACE/P/P/Q/Esc verified.

## Worktrees

- `feat/climate-logging` → `/tmp/opencode/wt-climate` — merged in PR #20.
- `feat/rendering` → `/tmp/opencode/wt-render` — merged in PR #21.
- `feat/docs` → `/tmp/opencode/wt-docs` — README, diagrams, spec, agent docs.
