# Bean World — Task Board

Legend: `[x]` done · `[~]` in progress · `[ ]` pending

| # | Task | Branch / worktree | Status |
|---|------|-------------------|--------|
| 1 | Weather-field box: right-hand text overflows the panel | `feat/rendering` | [x] |
| 2 | Eliminate `draw_text` PerformanceWarning via cached `arcade.Text` | `feat/rendering` | [x] |
| 3 | Logging (operational + business), configurable level in config and Makefile (default INFO) | `feat/climate-logging` | [x] |
| 4 | Rewrite `README.md` to match current code (LAST step) | `feat/docs` | [x] |
| 5 | Inspector/pointer misalignment (scaled displays + cell snapping) | `feat/render-playback` | [x] |
| 6 | Per-location climate gradients controlled by strategy config (N/S, W/E, centre-out, tuples) | `feat/climate-logging` | [x] |
| 7 | Grid rendering derived from `cell_size` / world cols-rows | `feat/render-playback` | [x] |
| 8 | `diagrams.md` with Mermaid class + sequence diagrams, linked from README | `feat/docs` | [x] |
| 9 | Align `spec.md`, `AGENTS.md` and `CLAUDE.md` with the code | `feat/docs` | [x] |
| 10 | Verify: compile, headless run, windowed screenshots, container verify | all | [x] |
| 11 | Commit → push → PR → merge → clean per `skills/git.md` | all | [x] |
| 12 | Pointer and click align exactly; selected cell and orange marker agree with cursor | `feat/render-playback` + `feat/barrier-climate` | [x] |
| 13 | Grid drawing honours `cell_size`; cells render correctly for beans | `feat/render-playback` | [x] |
| 14 | Playback-speed slider slows ticker without changing sim time; initial value from config | `feat/render-playback` | [x] |
| 15 | Barrier colour configurable, default yellow | `feat/barrier-climate` | [x] |
| 16 | Barriers span ≤ 3 grid cells per direction (3×3, 3×1, 1×2, …) | `feat/barrier-climate` | [x] |
| 17 | Barrier strategy: interface + implementation; colour and span limits in strategy | `feat/barrier-climate` | [x] |
| 18 | Weather strategy receives climate inputs (season, environment, world) | `feat/barrier-climate` | [x] |
| 19 | Season strategy owns sun amount; others derive luminosity/temperature from it | `feat/barrier-climate` | [x] |
| 20 | Update docs including diagrams | `main` | [x] |

## Verification log

- `python3 -m compileall sim` — OK on every branch.
- Headless (`BEAN_HEADLESS=1 BEAN_HEADLESS_FRAMES=300`) — Spring day/season/weather events emitted; climate context logged.
- Barriers: 6 yellow barriers generated; 4×1 rejected, 3×3 and 1×2 accepted; out-of-bounds rejected.
- Climate-aware weather: `adjusted_weather_weights()` reshapes by temperature/humidity/pressure/sun; rain→snow below freezing.
- Season sun: `solar_profile()` blends `sun_intensity`/`daylight_fraction` across the season boundary.
- Pointer round-trip: screen → world → cell_index returns the exact cell at multiple `cell_size` values; selected cell == hover cell.
- Grid: integer-snapped cell rectangles; 1:1 default window (scale 1.0, step = cell_size).
- Playback slider: sets `GameClock.time_scale` clamped to `[0.1, 4.0]`; `tick_rate` and `clock.tick` unchanged.
- Windowed (`DISPLAY=:0`) — window created, `app.start` / `app.window_created` logged.
- Container `make build` — OK.
- Container `make verify LOG_LEVEL=DEBUG BEAN_HEADLESS_FRAMES=300` — OK.
- PR #24 (barrier-climate) merged; PR #25 (render-playback) merged; `main` at `8ac4aab`, clean.

## Worktrees

- `feat/climate-logging` → merged in PR #20; worktree removed.
- `feat/rendering` → merged in PR #21; worktree removed.
- `feat/docs` → merged in PR #22; worktree removed.
- `feat/barrier-climate` → merged in PR #24; worktree removed.
- `feat/render-playback` → merged in PR #25; worktree removed.
- `main` at `8ac4aab`, clean, no worktrees.
