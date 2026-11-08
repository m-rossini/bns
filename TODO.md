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
| 16 | Barriers: density-based coverage, 3..8 cells per direction, non-deterministic by default (`seed=None`) | `main` (pending PR) | [x] |
| 17 | Barrier strategy: interface + implementation; colour and span limits in strategy | `feat/barrier-climate` | [x] |
| 18 | Weather strategy receives climate inputs (season, environment, world) | `feat/barrier-climate` | [x] |
| 19 | Season strategy owns sun amount; others derive luminosity/temperature from it | `feat/barrier-climate` | [x] |
| 20 | Update docs including diagrams | `main` | [x] |
| 21 | Controls box: config button, keys and slider must never overlap | `main` | [x] |
| 22 | Config screen crashes (`x_left`, `width`, `config.*` undefined) | `main` | [x] |
| 23 | Slider press was never hit-tested (dead `_slider_hit`) | `main` | [x] |
| 24 | Config screen generated from the config dataclasses | `main` | [x] |
| 25 | Bean creation strategy interface + `DensityBasedCreationStrategy` (current behaviour) | `feat/bean-movement` | [x] |
| 26 | `FixedAmountCreationStrategy` with configurable `total_beans`, reusing the placement strategy | `feat/bean-movement` | [x] |
| 27 | `IMovementStrategy` + `StraightLineMovementStrategy`: global direction/speed, in-place updates, edge bounce | `feat/bean-movement` | [x] |
| 28 | Detect and log bean↔barrier and bean↔bean collisions (no response yet) | `feat/bean-movement` | [x] |
| 29 | Run movement only while `PLAYING`; renderer draws live bean positions | `feat/bean-movement` | [x] |
| 30 | Movement logs (`bean.bounced`, `bean.collided_*`) move to DEBUG | `fix/run-and-log-levels` | [x] |
| 31 | `make run` opens the game window instead of running headless in a container | `fix/run-and-log-levels` | [x] |
| 32 | Lifespan genes, species age cap, senescence and old-age death telemetry | `main` (pending PR) | [x] |
| 33 | Versioned JSON snapshots (`BEAN_SAVE` / `BEAN_LOAD`) with deterministic restore | `main` (pending PR) | [x] |
| 34 | Comprehensive configuration + interface/implementation doc | `main` (pending PR) | [x] |

## Verification log

- `python3 -m compileall sim` — OK on every branch.
- Headless (`BEAN_HEADLESS=1 BEAN_HEADLESS_FRAMES=300`) — Spring day/season/weather events emitted; climate context logged.
- Barriers: 6 yellow barriers generated; 4×1 rejected, 3×3 and 1×2 accepted; out-of-bounds rejected.
- Barrier density redesign (pending PR): `density=0.01` targets 96 cells on the
  default grid (usually 3–4 obstacles, spans 3..8, `seed=None`); `test_barriers.py` added.
- Season variation (pending PR): year 1 is the configured baseline, later years
  re-roll inside `*_variation` ranges via `(season_seed, year, index)`; the seed
  is persisted in snapshots; `test_season.py` added.
- Climate-aware weather: `adjusted_weather_weights()` reshapes by temperature/humidity/pressure/sun; rain→snow below freezing.
- Season sun: `solar_profile()` blends `sun_intensity`/`daylight_fraction` across the season boundary.
- Pointer round-trip: screen → world → cell_index returns the exact cell at multiple `cell_size` values; selected cell == hover cell.
- Grid: integer-snapped cell rectangles; 1:1 default window (scale 1.0, step = cell_size).
- Playback slider: sets `GameClock.time_scale` clamped to `[0.1, 4.0]`; `tick_rate` and `clock.tick` unchanged.
- Windowed (`DISPLAY=:0`) — window created, `app.start` / `app.window_created` logged.
- Slider inside Controls box (bottom, no overlap with key bindings), verified by rect check.
- World scales up on maximised window; panel filled with ground colour (no grey border), verified via build_layout at 4480x1440.
- Precipitation thinned (subset of cells, fewer lines) so rain no longer floods the screen.
- Ground-colour legend (green = growing season, brown = dry/dormant) in the Environment box.
- Container `make build` — OK.
- Container `make verify LOG_LEVEL=DEBUG BEAN_HEADLESS_FRAMES=300` — OK.
- PR #24 (barrier-climate) merged; PR #25 (render-playback) merged; PR #27 (ui-polish) merged; `main` at `3bd6a82`, clean.
- Controls bands: button `y=172..196`, slider `y=24..30` — 142 px apart, no overlap, verified by `sim/tests/test_ui_layout.py`.
- Slider press starts a drag and changes `time_scale` (1.00 → 3.61 in the smoke run).
- `C` and the sidebar button both open one `ConfigWindow`; closing it returns the session to `PLAYING`; duplicate windows rejected.
- Config screen renders all 135 config values across three columns without error.
- `make test-cov` in-container: 82 tests pass, coverage report written to `htmlcov/`.
- `make test-cov` in-container after bean movement: 101 tests pass (creation + movement suites included).
- Coverage push (pending PR): 177 tests pass, TOTAL 80%. Every module is >=75%
  except `rendering/arcade_view.py` (15%): it subclasses `arcade.Window`, so
  all draw paths need a display and cannot run headless (no xvfb locally).
- Food system (pending PR): `IFoodSpawnStrategy` + `RandomFoodSpawnStrategy`,
  `FoodConfig`, magenta morsels anywhere, seasonal top-up toward target,
  nibble feeding capped by the new `digestion_capacity` gene with
  eaten/absorbed phenotype counters; 11 new behavior tests, 188 pass total.
- Food visibility + counters (pending PR): morsels drawn in poor/mid/rich size
  tiers (3 draw calls) with a brightness floor; sidebar census and end screen
  show morsel count plus total food energy.
  New behavior suites: `test_environment_behavior`, `test_daynight_energy`,
  `test_input_random`, `test_layout_behavior`, `test_main_behavior`. Also fixed
  a latent crash found by the new tests: `logger.exception(..., path=...)` on
  the corrupt-snapshot path in `main()` (plain loggers take no kwargs).
- Test targets split (pending PR): `make test` = fast container pytest (133 passed),
  `make test-cov` = full coverage report (`term-missing` + `htmlcov/` + `coverage.xml`,
  TOTAL 74%). Both bind-mount the repo with `:Z` + `$(USER_ARGS)` — required on
  SELinux-enforcing hosts, otherwise pytest gets `PermissionError: '/app'`.
- `make verify LOG_LEVEL=WARNING BEAN_HEADLESS_FRAMES=300`: headless run exits 0 with beans moving.
- Fixed-amount smoke: totals 50 / 200 / 1300 / 2000 each produced exactly that many beans.
- Movement smoke: bean x advanced by `speed × dt`; velocity seeded once, bounce flips the component.
- Movement logs: 0 `bean.bounced` / `collided` lines at `LOG_LEVEL=INFO`, 322 at `DEBUG` in a 60-frame headless run.
- `make run` now launches the window locally (`app.window_created width=1560 height=824`); headless lives at `make run-container` / `make run-headless`.

- Corpse + extinction: 118 tests passed; extinction tick froze clock, corpses and environment.
- Lifespan + persistence: 124 tests passed locally (6 new lifespan/persistence tests).
- Headless full run after lifespan: extinction at `ticks=2790`, corpses=83, ~11 s.
- Container `make verify BEAN_HEADLESS_FRAMES=200`: OK; initial snapshot written to `/app/saves`.
- Container snapshot resume: `BEAN_LOAD=saves/bean-...json` restored 1280 beans at tick 0 and ran.

## Worktrees

- `feat/climate-logging` → merged in PR #20; worktree removed.
- `feat/rendering` → merged in PR #21; worktree removed.
- `feat/docs` → merged in PR #22; worktree removed.
- `feat/barrier-climate` → merged in PR #24; worktree removed.
- `feat/render-playback` → merged in PR #25; worktree removed.
- `main` at `8ac4aab`, clean, no worktrees.
