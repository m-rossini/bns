# Bean World — Game Specification

Bean World is a pause-aware 2D simulation where beans live in a bounded arena
with day/night, seasons and per-cell weather. The project is written in Python
and uses [Arcade](https://api.arcade.academy/) only for physical presentation.

This document is the technical specification. It is kept aligned with the code;
[`README.md`](./README.md) is the usage-oriented reference and
[`diagrams.md`](./diagrams.md) holds the Mermaid diagrams.

Defaults quoted here come from `sim/config.py` (`DEFAULT_CONFIG`). Anything
marked *configurable* can be changed without editing code.

---

## 1. Project structure

```text
bns/
├── Containerfile              # container image (podman/docker)
├── Makefile                   # build, run, verify, clean targets
├── README.md                  # technical reference / usage
├── diagrams.md                # Mermaid diagrams
├── spec.md                    # this document
├── AGENTS.md                  # documentation index
├── CLAUDE.md                  # behaviour and ground rules
├── TODO.md                    # task board for the current change set
├── skills/
│   └── git.md                 # local git workflow
└── sim/
    ├── __init__.py
    ├── main.py                # entry point, fixed-step loop, headless mode
    ├── config.py              # ALL tunable configuration (single module)
    ├── components.py          # GameState, GameClock, GameSession, Barrier
    ├── container.py           # dependency-injection wiring
    ├── observability.py       # logging setup + structured business events
    ├── domain/
    │   ├── __init__.py
    │   ├── calendar.py        # tick -> day / clock / season / year
    │   ├── climate.py         # SolarProfile, ClimateContext
    │   ├── environment.py     # positional readings + gradient composition
    │   ├── gradient.py        # orientation-aware positional gradients
    │   ├── session.py         # concrete GameSession
    │   ├── visuals.py         # SeasonPalette, SkyPalette, CelestialState, SolarProfile
    │   └── world.py           # bounds, cells, orientation, wrap/clamp, barriers
    ├── implementations/
    │   ├── __init__.py
    │   ├── barrier/__init__.py   # BarrierStrategy (colour, span limits, placement)
    │   ├── daynight/__init__.py   # DayNightStrategy
    │   ├── season/__init__.py     # SeasonStrategy (owns sun via solar_profile)
    │   └── weather/__init__.py    # WeatherStrategy (climate-aware)
    ├── input/
    │   ├── __init__.py
    │   └── keyboard.py        # KeyboardInput state machine (+ set_time_scale)
    ├── interfaces/
    │   ├── __init__.py
    │   ├── barrier.py         # IBarrierStrategy
    │   ├── environment.py     # ICalendar, ISeasonStrategy, IDayNightStrategy,
    │   │                      # IWeatherStrategy, IEnvironment
    │   ├── renderer.py        # IRenderer protocol
    │   └── world.py           # IWorld
    ├── rendering/
    │   ├── __init__.py
    │   ├── arcade_view.py     # Arcade window, HUD, cached Text rendering
    │   └── layout.py          # WorldLayout: single draw + hit-test layout
    └── time/
        ├── __init__.py
        └── game_clock.py      # advance_clock() fixed-step accumulator + set_time_scale
```

There is no `sim/config_defaults.py`: `DEFAULT_CONFIG` lives at the bottom of
`sim/config.py`, and that module is the single source of truth for tunables.

---

## 2. Coordinate and time model

### 2.1 World units and cells

The world is measured in **world units**. It is divided into square cells of
`WorldConfig.cell_size`:

```text
cols = round(width / cell_size)
rows = round(height / cell_size)
```

Defaults: `1200 x 800` world units, `cell_size = 10` → `120 x 80 = 9600` cells.

- `World.cell_index(x, y)` maps a world position to `(col, row)`, clamped to
  the grid.
- `World.cell_center(col, row)` returns the centre of that cell.
- Weather, light and all readings are sampled per cell.
- The view applies one uniform world→screen scale. It never assumes a pixel
  size for a cell.

### 2.2 Time

`Calendar` is the only time authority. It derives everything from `tick`:

| Default | Value |
|---------|-------|
| `tick_rate` | `30.0` ticks/s |
| `ticks_per_day` | `1200` (40 s per day) |
| `ticks_per_season` | `4800` (4 days per season) |
| `start_tick` | `0` |

`SeasonStrategy` and `DayNightStrategy` both read the calendar; neither owns
the other. `Environment` composes them.

---

## 3. Domain model

### 3.1 GameState (`sim/components.py`)

| State | Meaning |
|-------|---------|
| `START` | Title screen; `SPACE` starts |
| `PLAYING` | Simulation running, time passing |
| `PAUSED` | Simulation frozen, overlay shown |
| `END` | Game over / user quit |

Only `GameSession` may change state. Systems query `session.state` before
running.

### 3.2 GameClock (`sim/components.py` + `sim/time/game_clock.py`)

Pause-aware fixed-step accumulator that decouples render frames from simulation
ticks.

Fields: `real_dt`, `sim_dt`, `accumulator`, `tick`, `paused` (default `True`),
`time_scale`.

`advance_clock(clock, real_dt, fixed_step) -> int` returns the number of ticks
executed this frame. When `paused` it returns `0` and keeps the accumulator.

`time_scale` changes *perception only*: it scales how fast simulated time seems
to pass without changing `tick_rate` or the fixed-step accumulation. Use
`set_time_scale(clock, value, vmin, vmax)` to set it, clamped to
`[vmin, vmax]`; `initial_time_scale(...)` returns the configured value clamped
to its range.

### 3.3 GameSession (`sim/components.py` + `sim/domain/session.py`)

Top-level logical state container: `state`, `world`, `environment`, `clock`,
`start_time`, `pause_time`, `end_reason`, `exit_requested`.

### 3.4 World (`sim/domain/world.py`)

Holds arena bounds, the derived cell grid, orientation, wrap behaviour and
static barriers.

- `width`, `height`, `cell_size`
- `cols`, `rows` (derived)
- `orientation` — the default climate-gradient direction
- `wrap_around`
- `barrier_strategy` — the `IBarrierStrategy` that owns colour and span rules
- `barriers: list[Barrier]`
- `add_barrier(barrier)` — validates against `barrier_strategy` (span ≤ max
  cells per direction, inside bounds) before appending
- `remove_barrier(barrier_id)`
- `is_inside(x, y)` / `clamp_or_wrap(x, y)`
- `cell_index(x, y)` / `cell_center(col, row)`

`DEFAULT_CONFIG` creates 6 yellow barriers via the barrier strategy; the
view draws them. The type and methods are extension points for the bean
systems.

### 3.5 Barrier (`sim/components.py`)

Static obstacle: `id`, `kind` (`"rect"` or `"circle"`), `x`, `y`, `width`,
`height`, `radius`, `color`.

Rules live in the barrier strategy (`IBarrierStrategy`):

- `color` — fill colour; default yellow `(255, 208, 64)`, configurable.
- `max_span_cells` — a barrier may span at most this many grid cells per
  direction (default 3), so 3×3, 3×1, 1×2 and 2×2 are valid while 4×1 is
  rejected.
- `BarrierStrategy.create_barriers(world)` — deterministic placement from a
  seed, with bounds and span validation.

### 3.6 Environment (`sim/domain/environment.py`)

The only object that turns the strategies into positional readings. It holds a
`Gradient` per reading and composes them as follows:

```text
light(x, y)       = sun_altitude * local_shading * season_light
                    * light_gradient(x, y) * weather_light_factor
temperature(x, y) = season_base + swing * (2*light - 1)
                    + weather_temperature_offset
                    + temperature_gradient(x, y) + microclimate(x, y)
humidity(x, y)    = season_humidity + weather_humidity_offset
                    + humidity_gradient(x, y) + microclimate(x, y)
pressure(x, y)    = season_pressure + weather_pressure_offset
                    + pressure_gradient(x, y) + microclimate(x, y)
```

- A strategy set to `None` means **static mode**: that reading falls back to a
  documented constant and the simulation keeps running.
- The palette is cached per tick, so repeated `temperature_at` calls in one
  tick do not re-interpolate the season colour.
- `advance_tick()` advances the calendar once and notifies the weather
  strategy, then emits business events for day/season/weather changes and, at
  `DEBUG`, periodic reading samples.

### 3.7 Gradient (`sim/domain/gradient.py`)

```python
@dataclass(frozen=True)
class Gradient:
    orientation: str = "north_south"
    start: float = 0.0
    end: float = 1.0
```

`factor(x, y, width, height)` returns a normalised `0..1` position along the
orientation; `value(...)` interpolates `start → end`. The same primitive is
used for numeric readings and for the season ground colour.

Orientations: `north_south`, `south_north`, `west_east`, `east_west`,
`centre_out`, `out_centre`, `diagonal_up`, `diagonal_down`. Unknown names fall
back to `north_south` and log a warning, so a configuration typo never stops
the simulation.

---

## 4. Interfaces

### 4.1 `sim/interfaces/environment.py`

```python
class ICalendar(ABC):
    tick, day, day_fraction, clock, season, season_index,
    season_progress, day_of_season, year
    advance(ticks=1), reset()

class ISeasonStrategy(ABC):
    ticks_per_season, season_names
    palette(calendar) -> SeasonPalette
    solar_profile(calendar) -> SolarProfile   # how much sun the world gets
    get_season_name(calendar) -> str
    weather_weights(season) -> dict

class IDayNightStrategy(ABC):
    ticks_per_day
    light_at(calendar, x, y, solar=None) -> float   # consumes SolarProfile
    phase(calendar, solar=None) -> str
    celestial(calendar, solar=None) -> CelestialState
    sky_palette() -> SkyPalette

class IWeatherStrategy(ABC):
    weather                     # aggregate condition for the HUD
    weather_at(x, y)            # per-cell
    weather_at_cell(col, row)
    update(tick, climate)       # climate: ClimateContext
    reset()

class IBarrierStrategy(ABC):
    color                       # fill colour (default yellow)
    max_span_cells              # span cap per direction (default 3)
    span_cells(barrier, world) -> (cols, rows)
    validate(barrier, world)    # raises ValueError on rule breach
    create_barriers(world) -> list[Barrier]

class IEnvironment(ABC):
    tick, calendar, weather_strategy, season_strategy, daynight_strategy
    season, phase, weather, light_level, palette
    solar                       # SolarProfile from the season strategy
    celestial                   # CelestialState from day/night
    climate_context() -> ClimateContext   # snapshot for the weather strategy
    weather_at(x, y), light_at(x, y), humidity_at(x, y),
    pressure_at(x, y), temperature_at(x, y)
    advance_tick(), reset()
```

### 4.2 `sim/interfaces/world.py`

`IWorld` — `width`, `height`, `cell_size`, `cols`, `rows`, `orientation`,
`wrap_around`, `barrier_strategy`, `barriers`, `add_barrier` /
`remove_barrier`, `set_barrier_strategy`, `is_inside`, `clamp_or_wrap`,
`cell_index`, `cell_center`.

### 4.3 `sim/interfaces/renderer.py`

`IRenderer` (runtime-checkable `Protocol`): `draw_start_screen()`,
`draw_playing(session)`, `draw_paused(session)`, `draw_end_screen(session)`,
`flip()`.

`Protocol` is used instead of `ABC` to avoid metaclass conflicts with
`arcade.Window`.

---

## 5. Implementations

### 5.1 DayNightStrategy

- Consumes the season's `SolarProfile` (peak `sun_intensity` and
  `daylight_fraction`) instead of a `season_factor` multiplier.
- Places the sun inside the season's daylight window (centred on 0.5 day
  fraction); altitude 0 at night.
- Sun and moon run independent cycles (`sun_speed`, `moon_speed`,
  `moon_phase_offset`), so they are not locked to one global cycle.
- `light_at` = sun arc × smooth local shading × sun intensity.
  `local_shading` and `shading_scale_x/y` shape the terrain/cover variation.
- `phase`: `night`, `dawn`, `day`, `dusk` using `night_threshold` and
  `twilight_threshold`.
- `celestial`: sun/moon arc progress, visibility and moon illumination.
- `sky_palette`: the configured sky, sun, moon and star colours.

### 5.2 SeasonStrategy

- Seasons are a **list** in configuration: one, two, four or eight need no code
  change.
- Default order: `Spring → Summer → Autumn → Winter`, 4 days each.
- Owns **how much sun** the world gets: `solar_profile(calendar)` blends the
  current season's `sun_intensity` and `daylight_fraction` into the next
  season's over the final quarter of the season, so the hand-off is continuous.
- `palette(calendar)` returns `SeasonPalette` with the season name, ground
  colour, detail colours, temperature baseline/swing, humidity, pressure,
  `sun_intensity`, `daylight_fraction` and `ground_meaning` (the season's
  human-readable ground-colour description, shown in the Environment legend).
- The ground colour is season-driven, not random: green shades mark growing
  seasons (spring/summer) and brown shades mark dry or dormant seasons
  (autumn/winter). This is shown in the Environment box legend.
- Ground colour: if `SeasonConfig.ground_gradient` is set, it is interpolated
  `start → end` over the season's progress. Otherwise `ground_color` blends
  toward the next season's colour.
- `weather_weights(season)` drives the weather field.

### 5.3 WeatherStrategy

- Per-cell field, not uniform: a patchy **background** condition plus
  `front_count` circular **fronts**.
- A new field is built every `change_interval` ticks (`600` = 20 s), derived
  deterministically from `(seed, interval, season)`.
- `update(tick, climate)` receives a `ClimateContext` (season, world geometry,
  temperature, humidity, pressure, solar profile) and reshapes the season's
  weights via `ClimateContext.adjusted_weather_weights()`: rain falls as snow
  below freezing, storms need warmth and moisture, clear skies dominate dry air.
- Front radius comes from `front_radius_min_cells` / `front_radius_max_cells`
  (in cells; `0` = derive from the grid).
- `front_drift_cells` optionally shifts fronts between rebuilds.
- Each cell takes the most severe condition among the background and every
  front covering it. Severity: `clear < cloudy < rain = snow < storm`.
- Conditions: `clear`, `cloudy`, `rain`, `storm`, `snow`. Snow only appears in
  seasons whose weights allow it.

### 5.4 BarrierStrategy

- Implements `IBarrierStrategy`; owns colour and span rules.
- Default colour yellow `(255, 208, 64)`, configurable via `BarrierConfig.color`.
- `max_span_cells` caps span per direction (default 3); `min_span_cells`
  (default 1); `count` barriers generated from `seed` with a `margin_cells`
  border margin.
- Barriers are axis-aligned rectangles snapped to the cell grid; placement is
  deterministic and non-overlapping (best-effort reshuffle).
- `validate()` rejects unknown kinds, non-positive sizes, out-of-bounds, and
  spans exceeding `max_span_cells`.

---

## 6. Rendering (`sim/rendering/arcade_view.py`)

`ArcadeView` extends `arcade.Window` and structurally implements `IRenderer`.

Screens:

- **START** — sky, stars at night, sun/moon arc, title panel with controls.
- **PLAYING** — world on the right, stacked information boxes on the left.
- **PAUSED** — playing scene dimmed with a `PAUSED` overlay.
- **END** — `GAME OVER`, reason, restart hint.

Layout:

- A fixed left sidebar (`300..360` px, ~30 % of the viewport) with stacked
  boxes: **Time, Day, Season, Environment, Inspector, Weather field,
  Controls**.
- The world uses the remaining area and the full height; it never sits under a
  box.
- Day and season progress are separate boxes, not a joined bar.

Rendering contract:

- **Text** — every string is drawn with cached `arcade.Text` objects.
  `arcade.draw_text` is never called: it re-lays out and re-uploads a texture
  per call, is slow and raises `PerformanceWarning`.
- **WorldLayout** — a single layout object (`sim/rendering/layout.py`) owns the
  world → screen projection and the cell grid. Drawing (grid, cells, markers,
  barriers) and hit-testing (mouse motion/press) share this one layout, so the
  selected cell, the orange marker and the cursor always agree. Cell steps are
  integer-snapped to whole pixels.
- **Grid** — one line per cell boundary, derived from `world.cell_size`,
  `world.cols` and `world.rows`. The drawn world spans `cols*cell_size` by
  `rows*cell_size`, so lines always land on cell edges. Cells render in screen
  units that honour `cell_size`, ready for beans to be drawn per cell.
- **Barriers** — drawn as filled cell-aligned rectangles in the barrier
  strategy's colour (default yellow), with a dark outline.
- **Selection** — stored as an integer `(col, row)`. The orange marker, the
  crosshair and the readings all derive from it, so they cannot disagree.
- **Pointer mapping** — layout uses the active viewport size and mouse
  coordinates are scaled from the window size, so clicks line up on HiDPI or
  scaled displays. The layout is recomputed when the viewport changes.
- **Playback-speed slider** — in the Controls box. Drag to slow / speed the
  perceived ticker; it sets `GameClock.time_scale` (clamped to
  `time_scale_min`/`time_scale_max`) and never changes `tick_rate` or
  sim-time progression (`clock.tick`). Initial value from
  `TimeConfig.initial_time_scale`.
- **Weather field box** — live census of cells and percentage per condition;
  rows are limited to the panel height and overflow is summarised as
  `+N more conditions`.

The default window is sized for 1:1 world rendering (1 world unit = 1 screen
pixel) plus the sidebar, so the grid is crisp at startup.

`ArcadeView` never mutates domain state: it reads a snapshot of `GameSession`.
Hover and selection are view-local.

`ArcadeView` must not override `flip()`: pyglet calls it after `on_draw` to run
`glXSwapBuffers`. A no-op override draws into the back buffer only, so the
window shows a stale front buffer even though `arcade.get_image()` returns a
correct screenshot.

---

## 7. Input (`sim/input/keyboard.py`)

`KeyboardInput` is the only writer of `GameSession.state`.

| State | Key | Action |
|-------|-----|--------|
| START | `SPACE` | → PLAYING, unpause clock, set `start_time` |
| START | `P` | → PAUSED, pause clock |
| START | `Esc` | → END, reason `user quit` |
| PLAYING | `P` | → PAUSED, pause clock |
| PLAYING | `Q` / `Esc` | → END, reason `user quit` |
| PAUSED | `P` | → PLAYING, unpause clock |
| PAUSED | `Q` / `Esc` | → END, reason `user quit` |
| END | `SPACE` | restart: fresh clock, environment reset |
| END | `Q` / `Esc` | set `exit_requested`; the loop closes the window |

`KeyboardInput.set_time_scale(value)` clamps `GameClock.time_scale` to
`[time_scale_min, time_scale_max]` and emits `session.time_scale`. It changes
perception only: `tick_rate` and `clock.tick` are untouched. The slider in the
view calls this via the input handler.

Key codes are GLFW codes: `SPACE=32`, `P=112`, `Q=113`, `Esc=65307`.

Mouse (view-local): left click pins the cell under the cursor; clicking outside
the world clears the selection. Hover highlights the cell but is not pinned.

---

## 8. Time and game loop (`sim/main.py`)

```python
fixed_step = 1.0 / config.tick_rate       # 30 ticks/s

on_update(dt):
    real_dt = now - last_time
    ticks_executed = advance_clock(session.clock, real_dt, fixed_step)
    for _ in range(ticks_executed):
        environment.advance_tick()        # one environment tick per sim tick
    if session.state == PLAYING:
        pass                              # bean systems (placeholder)
    if session.exit_requested:
        view.close()
        arcade.exit()
```

- `BEAN_HEADLESS=1` runs a bounded deterministic loop at `1/60 s` per frame,
  never imports Arcade/OpenGL and auto-starts the session (there is no input to
  press `SPACE`).
- `BEAN_HEADLESS_FRAMES=N` bounds the number of frames (default `600`), so the
  container exits instead of hanging. The run ends with a
  `session.headless_finished` business event.
- The windowed path blocks until the window is closed.

---

## 9. Configuration (`sim/config.py`)

Pure-Python dataclasses, no YAML/JSON. `DEFAULT_CONFIG` is a
`SimulationConfig` and the only object `main()` reads.

### 9.1 Dataclasses

| Dataclass | Owns |
|-----------|------|
| `WorldConfig` | `width=1200`, `height=800`, `cell_size=10`, `orientation`, `wrap_around` |
| `TimeConfig` | `ticks_per_day=1200`, `ticks_per_season=4800`, `start_tick=0`, `initial_time_scale=1.0`, `time_scale_min=0.1`, `time_scale_max=4.0` |
| `BarrierConfig` | `color=(255,208,64)` yellow, `max_span_cells=3`, `min_span_cells=1`, `count=6`, `seed=4242`, `margin_cells=1` |
| `BeanPlacementConfig` | `strategy_name`, `density_tier`, `variance`, `seed`, gender ratios, `gender_colors`, strategy params |
| `GradientConfig` | `start`, `end`, `orientation` (empty inherits the world) |
| `SeasonConfig` | name, colours, `ground_gradient`, climate baseline, `sun_intensity`, `daylight_fraction`, weather weights |
| `DayNightConfig` | sun/moon, shading, thresholds, sky colours |
| `WeatherConfig` | interval, seed, front count/radius/drift, coverage, condition offsets |
| `EnvironmentConfig` | strategy names, four climate gradients, `microclimate` |
| `LoggingConfig` | level, format, date format, business/readings switches |
| `SimulationConfig` | all of the above + `tick_rate=30.0`, `debug=False` |

### 9.2 Seasons

```python
SeasonConfig(
    name="Spring",
    ground_color=(96, 170, 88),
    ground_gradient=((82, 148, 78), (128, 196, 104)),  # (start, end)
    detail_colors=[(250, 246, 180), (248, 186, 214), (232, 248, 236)],
    base_temperature=14.0,
    temperature_swing=7.0,
    humidity=0.55,
    pressure_hpa=1012.0,
    sun_intensity=0.95,
    daylight_fraction=0.50,
    weather_weights={"clear": 30, "cloudy": 30, "rain": 30, "storm": 10, "snow": 0},
)
```

Defaults: Spring (`0.95` sun / `0.50` daylight), Summer (`1.15` / `0.60`),
Autumn (`0.82` / `0.45`), Winter (`0.55` / `0.34`). `SeasonStrategy`
publishes a `SolarProfile` blending these across the season boundary.
`ground_gradient=None` falls back to blending `ground_color` toward the next
season.

The `light_influence`/`season_light_influence` fields are removed: the season
strategy owns the sun via `solar_profile()` and day/night consumes it.

### 9.3 Positional gradients

Each reading has a `GradientConfig`; `orientation=None` inherits
`WorldConfig.orientation`.

| Reading | Default gradient |
|---------|------------------|
| Temperature | `GradientConfig(-4.0, 4.0)` |
| Humidity | `GradientConfig(-0.12, 0.12)` |
| Pressure | `GradientConfig(-6.0, 6.0)` |
| Light | `GradientConfig(0.88, 1.08)` |

```python
DEFAULT_CONFIG.world.orientation = "west_east"
DEFAULT_CONFIG.environment.temperature_gradient = GradientConfig(
    -6.0, 6.0, orientation="centre_out"
)
DEFAULT_CONFIG.environment.microclimate = 0.5
```

### 9.4 Weather

```python
WeatherConfig(
    change_interval=600,
    seed=1337,
    front_count=3,
    background_coverage=0.6,
    front_radius_min_cells=2,
    front_radius_max_cells=6,
    front_drift_cells=0.0,
    background_patch_scale=1.0,
)
```

Physical effects per condition (defaults):

| Condition | Temperature | Humidity | Pressure | Light |
|-----------|-------------|----------|----------|-------|
| clear | +2.0 °C | −0.10 | +4.0 hPa | 1.00 |
| cloudy | 0.0 | +0.02 | −3.0 | 0.82 |
| rain | −2.0 | +0.20 | −8.0 | 0.68 |
| storm | −4.0 | +0.25 | −18.0 | 0.50 |
| snow | −5.0 | +0.08 | −5.0 | 0.85 |

### 9.5 Barriers

```python
BarrierConfig(
    color=(255, 208, 64),     # yellow
    max_span_cells=3,         # ≤ 3 cells per direction
    min_span_cells=1,
    count=6,
    seed=4242,
    margin_cells=1,
)
```

`BarrierStrategy` owns colour and span limits; `World.add_barrier` validates
against it. Six yellow barriers are generated by `DEFAULT_CONFIG`.

### 9.6 Bean Placement (`sim/domain/spawn_controller.py`, `sim/domain/beans.py`)

Initial unicellular beans are spawned by a :class:`sim.domain.spawn_controller.SpawnController`
driven by `sim/config.BeanPlacementConfig`. The controller:

1. **Calculates target population ``N``** from world area × density coefficient ×
   stochastic variance (area-based dynamic population calculus).
2. **Generates positions** via a configurable :class:`sim.interfaces.placement.IPlacementStrategy`
   (``poisson_disc``, ``symmetrical``, ``colony_cluster``, ``center_to_border``,
   ``border_to_center``, ``linear_gradient``, ``resource_gradient``).
3. **Assigns gender + color** via an
   :class:`sim.interfaces.gender.IGenderController` whose ratio percentages must
   sum exactly to 100.
4. **Instantiates** :class:`sim.components.Bean` entities, stored on
   `GameSession.beans`, each drawn as a small cross in its gender color
   (blue = male, red = female).

Logged events: ``spawn.started``, ``spawn.positions_generated``,
``gender.assigned``, ``spawn.finished``.

`BeanPlacementConfig` holds the strategy name, density tier, variance, seed,
gender ratios and per-gender color mappings. Default: poisson_disc placement,
average density, 50/50 male/female, male blue `(0, 0, 255)`, female red
`(255, 0, 0)`.

**Collision-free placement**: every bean position is validated before
acceptance. Beans do not overlap each other (minimum distance = 2 ×
`bean_radius`), do not overlap barriers, and stay fully inside the world
bounds (margin = `bean_radius`). The shared helper
`sim.domain.placement_utils.is_valid_bean_position()` is used by all
placement strategies to guarantee these invariants.

### 9.7 Logging

`LoggingConfig(level="INFO", business=True, readings=True,
readings_interval=60)`. `BEAN_LOG_LEVEL` overrides `level` at runtime; the
Makefile exposes it as `LOG_LEVEL`. See §12.

### 9.8 Testing

Tests live in `sim/tests/` and are run with pytest. Coverage is measured with
`coverage` and reported via `pytest-cov`.

| Make target | Command | Purpose |
|-------------|---------|---------|
| `make test-pytest` | `pytest sim/tests/ -v` | Run all tests |
| `make test-cov` | `pytest sim/tests/ --cov=sim` | Run with coverage report |
| `make test` | `test-pytest` + `test-cov` | Full local test suite |
| `make test-container` | `docker run ... pytest ...` | Run tests inside the container (preferred) |

Coverage target: **100% line coverage** on `sim/domain/`,
`sim/implementations/placement/`, `sim/implementations/gender.py`, and
`sim/domain/placement_utils.py`.

---

## 11. Dependency injection (`sim/container.py`)

`Container(config: SimulationConfig)` builds, in order:

1. `self.world` from `config.world`
2. `self.calendar` from `config.time` + season names
3. `self.environment` from the calendar, world, resolved strategies and
   `EnvironmentConfig` / `WeatherConfig` / `LoggingConfig`
4. `self.session` from the world and environment
5. `self.debug` from `config.debug`

Strategy names are resolved case-insensitively. `None` disables that strategy
(static mode). Accepted values: `DayNightStrategy` / `daynight`,
`SeasonStrategy` / `season`, `WeatherStrategy` / `weather`, plus `default`.
Unknown names raise `ValueError`.

---

## 12. Logging and instrumentation (`sim/observability.py`)

Two streams, both under the `bean.*` logger namespace:

- **operational** — startup, shutdown, wiring, weather rebuilds, configuration
  problems.
- **business** — what the player did and how the world reacted. Each entry is
  one line: `event=<name> key=value ...` with sorted keys.

Level resolution:

1. `BEAN_LOG_LEVEL` environment variable
2. `SimulationConfig.logging.level`
3. `INFO`

Events: `app.start`, `app.window_created`, `app.window_closing`, `app.stop`,
`container.built`, `session.started`, `session.paused`, `session.resumed`,
`session.restart`, `session.quit`, `session.closed`,
`environment.day_changed`, `environment.season_changed`,
`environment.weather_changed`, `environment.reading` (DEBUG),
`weather.field_rebuilt`, `weather.front` (DEBUG), `season.palette` (DEBUG),
`ui.cell_inspected`.

Reading samples are emitted only at `DEBUG` and at most once per
`readings_interval` ticks.

---

## 13. Containers and tooling

### 13.1 Containerfile

`Dockerfile` is not the source of truth; `Containerfile` is, and both podman
and docker understand it.

The image:

- Base `python:3.10-slim`.
- Installs OpenGL/Arcade runtime libraries (`libegl1`, `libgles2`, `libgl1`,
  `libgl1-mesa-dri`, `libglib2.0-0`, `libsm6`, `libxext6`, `libxrender1`,
  `libxi6`, `libfontconfig1`) plus `xvfb` and `xauth`.
- Creates a venv at `/opt/venv` and installs `arcade`.
- Copies `sim/` to `/app/sim/`.
- Defaults `BEAN_HEADLESS=1`, `BEAN_HEADLESS_FRAMES=600`,
  `PYTHONUNBUFFERED=1`.
- CMD `python -m sim.main`.

Headless mode never imports Arcade/OpenGL, so the default container run needs
no display server. `xvfb-run` must not be PID 1: Xvfb skips its SIGUSR1
readiness signal when its parent is init, so prefer `make run-container-ui`,
which bind-mounts the host X11 socket.

### 13.2 Makefile targets

| Target | Description |
|--------|-------------|
| `make venv` | Create the local venv (stdlib `venv`, `virtualenv` fallback) |
| `make install` | Install arcade into the venv (stamp-guarded) |
| `make test` | Local compile + bounded headless run |
| `make verify` | Build + bounded headless run in-container, foreground |
| `make run` | Alias for `run-container` (detached, headless) |
| `make run-local` | Run locally with a window (blocks) |
| `make run-headless` | Bounded headless run locally |
| `make build` | Build the container image |
| `make run-container` | Start the headless container detached |
| `make run-container-ui` | Start the UI container detached (needs X11) |
| `make logs` | Follow the detached container's output |
| `make status` | Show container status, including exited |
| `make stop` | Stop and remove the detached container |
| `make check-env` | Show Python/venv/container runtime status |
| `make clean` | Remove venv, caches, container, image |
| `make help` | Show help |

Container runtime detection prefers `podman`, falls back to `docker`, and
errors if neither exists.

`LOG_LEVEL` (default `INFO`) is exported as `BEAN_LOG_LEVEL` to every run
target:

```bash
make run LOG_LEVEL=DEBUG
make verify LOG_LEVEL=DEBUG
```

Containers run detached under the fixed name `bean-world`; `make stop` or the
next start removes a previous container. `make verify` is the opposite: it runs
`--rm` in the foreground and exits with the container's status, so it is the
cheapest end-to-end check.

---

## 14. How to run

```bash
# Local, windowed
make venv && make install && make run-local

# Local, bounded headless
make run-headless
BEAN_HEADLESS=1 BEAN_HEADLESS_FRAMES=2000 python -m sim.main

# Container, detached headless
make build && make run-container && make logs

# Container, foreground verification
make verify LOG_LEVEL=DEBUG BEAN_HEADLESS_FRAMES=300

# Container, windowed through X11
DISPLAY=:0 make run-container-ui
```

Environment variables:

| Variable | Effect |
|----------|--------|
| `BEAN_HEADLESS=1` | Run without a window; no Arcade/OpenGL import |
| `BEAN_HEADLESS_FRAMES=N` | Frame limit for headless mode (default 600) |
| `BEAN_LOG_LEVEL=LEVEL` | Override the log level at runtime |
| `LOG_LEVEL=LEVEL` | Make-level alias, exported as `BEAN_LOG_LEVEL` |

---

## 15. Current status

### Implemented

- Domain: `GameSession`, `GameClock`, `GameState`, `World`, `Environment`,
  `Calendar`, `Gradient`, `Barrier`, `SolarProfile`, `ClimateContext`,
  `WorldLayout`.
- DI container wiring configuration to domain objects, with strategy
  resolution, static fallbacks and barrier placement.
- Environment strategies: day/night, seasons, weather — each optional.
- Season strategy owns the sun: `solar_profile()` blends `sun_intensity` and
  `daylight_fraction` across the season boundary.
- Day/night consumes `SolarProfile`; weather receives a `ClimateContext` and
  reshapes season weights by temperature, humidity, pressure and sun.
- Barrier strategy (`IBarrierStrategy` + `BarrierStrategy`): configurable
  colour (default yellow), span capped at 3 cells per direction, validated on
  `World.add_barrier`. `DEFAULT_CONFIG` creates 6 yellow barriers.
- Bean placement & gender: `SpawnController` + `IPlacementStrategy` +
  `IGenderController`; `BeanPlacementConfig` drives strategy selection,
  density tier, variance and gender ratios/colors. `DEFAULT_CONFIG` spawns
  ~1300 beans (poisson_disc, average density, 50/50 male/female), drawn as
  small crosses in gender color. All positions are collision-free (no bean-bean,
  bean-barrier, or bean-border overlap) via `placement_utils.is_valid_bean_position()`.
- Automated tests in `sim/tests/` with pytest + coverage: placement strategies,
  gender controller, spawn controller, config validation.
- Positional temperature, humidity, pressure and light with configurable
  gradients (N/S, W/E, centre-out, out-centre, diagonals).
- Rendering: start/playing/paused/end screens, animated sky, seasons, per-cell
  weather, HUD sidebar, cell-aligned grid honouring `cell_size`, pinned
  inspector, barrier drawing, playback-speed slider.
- `WorldLayout`: single source of truth for draw + hit-test; pointer/click
  align exactly with the selected cell and orange marker.
- Default 1:1 window sizing; integer-snapped cell rectangles.
- Cached `arcade.Text` rendering; no `draw_text` `PerformanceWarning`.
- Input: `SPACE` / `P` / `Q` / `Esc`, hover and click-to-inspect, slider sets
  `GameClock.time_scale` (perception only).
- Pause-aware fixed-step clock and a bounded headless mode.
- Structured operational and business logging with a runtime level.
- Container image plus Makefile targets, including `make verify`.

### Not implemented

- Bean movement, collision, eating, reproduction — the systems hook in
  `main.py` is a placeholder. Initial bean placement IS implemented.
- Automated tests and lint/typecheck configuration.
