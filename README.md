# Bean World

A pause-aware 2D world simulation with a calendar-driven day/night cycle,
configurable seasons, per-cell weather and position-dependent climate readings.
Rendering uses [Arcade](https://api.arcade.academy/); the domain layer has no
OpenGL dependency and runs headless.

The current implementation is the reference for this document. The original
project brief lives in [`spec.md`](./spec.md); architecture diagrams live in
[`diagrams.md`](./diagrams.md).

---

## Quick start

```bash
# Local development
make venv
make install
make run-local          # opens the window

# Bounded headless run (no display, no OpenGL import)
make run-headless
BEAN_HEADLESS=1 BEAN_HEADLESS_FRAMES=2000 python -m sim.main

# Container (podman preferred, docker fallback)
make build
make run                # headless, detached
make logs               # follow it
make verify             # headless, foreground, exits with the logs
make run-container-ui   # windowed through the host X11 socket
```

Requires Python 3.10+ and `arcade` (installed by `make install`).

---

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Start, or restart after the end screen |
| `P` | Pause / resume |
| `Q` / `Esc` | Quit (works from every state) |
| Left click | Inspect a cell; the selection stays pinned |
| Click outside the world | Clear the pinned selection |
| Drag the speed slider (sidebar "Controls") | Slow / speed the perceived ticker |

The simulation clock only advances while the session is `PLAYING`. `START` and
`PAUSED` freeze simulation time while still redrawing the screen. The speed
slider changes *perception* only: it scales how fast the ticker appears to run
without touching `tick_rate` or sim-time progression (`clock.tick`).

---

## What is modelled

- **Calendar** — the single time authority: tick → day, clock, season, year.
- **Seasons** — any number, defined entirely by configuration. Each season has
  a colour gradient, temperature baseline and swing, humidity, pressure, sun
  intensity, daylight fraction, weather weights and a ground-colour meaning.
  The ground colour is season-driven, not random: green shades mark growing
  seasons (spring/summer) and brown shades mark dry or dormant seasons
  (autumn/winter). The meaning is shown in the Environment box legend and is
  owned by the season strategy's config (`SeasonConfig.ground_meaning`).
- **Day/night** — sun altitude, dawn/dusk/night phases, moon phase, sky palette,
  and smooth local shading of the light curve.
- **Weather** — a per-cell field made of a patchy background condition plus
  moving circular fronts. Neighbouring cells can show different conditions.
- **Environment** — composes the three strategies into positional readings:
  temperature (°C), light (0..1), humidity (0..1) and atmospheric pressure (hPa).
- **Barriers** — static, cell-aligned rectangular obstacles owned by a barrier
  strategy (`IBarrierStrategy` + `BarrierStrategy`). Each barrier has a
  configurable colour (default yellow) and may span at most 3 grid cells in
  either direction (3×3, 3×1, 1×2, …). The container generates a deterministic
  set at startup and `World.add_barrier` validates spans and bounds.
- **Season-owned sun** — `SeasonStrategy.solar_profile()` publishes how much sun
  the world gets (`sun_intensity`, `daylight_fraction`), blending into the next
  season over the final quarter of the season. Day/night and weather derive
  their values from it.
- **Climate-aware weather** — `IWeatherStrategy.update(tick, ClimateContext)`
  receives season, world geometry, temperature, humidity, pressure and the
  solar profile, and reshapes the season's weather weights (rain falls as snow
  below freezing, storms need warmth and moisture, etc.).
- **Rendering** — a full-height world on the right and a stack of information
  boxes on the left. The grid is drawn from the configured cell size.
- **Bean placement** — initial unicellular beans are spawned by a
  :class:`sim.domain.spawn_controller.SpawnController` driven by
  `sim/config.BeanPlacementConfig`. The controller:

  * Calculates target population from world area × density tier × variance
    (area-based dynamic population calculus).
  * Generates positions via a configurable :class:`IPlacementStrategy`
    (poisson_disc, symmetrical, colony_cluster, center_to_border,
    border_to_center, linear_gradient, resource_gradient).
  * Assigns gender identity + visual color via an
    :class:`IGenderController` whose ratio percentages must sum to exactly 100.
  * Instantiates :class:`sim.components.Bean` entities, stored on
    `GameSession.beans`, each drawn as a small cross in its gender color
    (blue = male, red = female).

  Logged events: `spawn.started`, `spawn.positions_generated`,
  `gender.assigned`, `spawn.finished`.


---

## Architecture

```text
sim/
├── config.py                 # ALL tunable configuration (single module)
├── components.py             # GameState, GameClock, GameSession, Barrier
├── container.py              # dependency-injection wiring
├── observability.py          # logging setup + structured business events
├── main.py                   # entry point, fixed-step loop, headless mode
├── domain/
│   ├── calendar.py           # tick -> day / clock / season / year
│   ├── climate.py            # SolarProfile, ClimateContext
│   ├── environment.py        # positional readings + gradient composition
│   ├── gradient.py           # orientation-aware positional gradients
│   ├── session.py            # concrete GameSession
│   ├── visuals.py            # SeasonPalette, SkyPalette, CelestialState, SolarProfile
│   └── world.py              # bounds, cells, orientation, wrap/clamp, barriers
├── interfaces/
│   ├── barrier.py            # IBarrierStrategy
│   ├── environment.py        # ICalendar, ISeasonStrategy, IDayNightStrategy,
│   │                         # IWeatherStrategy, IEnvironment
│   ├── renderer.py           # IRenderer protocol
│   └── world.py              # IWorld
├── implementations/
│   ├── barrier/__init__.py   # BarrierStrategy (colour, span limits, placement)
│   ├── daynight/__init__.py  # DayNightStrategy
│   ├── season/__init__.py    # SeasonStrategy (owns sun via solar_profile)
│   └── weather/__init__.py   # WeatherStrategy (climate-aware)
├── input/keyboard.py         # KeyboardInput state machine (+ set_time_scale)
├── rendering/
│   ├── __init__.py
│   ├── arcade_view.py        # Arcade window, HUD, cached Text rendering
│   └── layout.py             # WorldLayout: single draw + hit-test layout
├── time/game_clock.py        # pause-aware fixed-step accumulator + set_time_scale
└── __init__.py
```

The dependency direction is strict: `domain` and `interfaces` never import
`rendering` or `arcade`. `ArcadeView` reads a `GameSession` snapshot and never
mutates domain state. See [`diagrams.md`](./diagrams.md) for the class and
sequence diagrams.

### Time authority

`Calendar` owns the tick. `SeasonStrategy` and `DayNightStrategy` are siblings
that both read it; neither owns the other. `Environment` owns the composition
and is the only object that produces positional readings. `SeasonStrategy`
publishes a `SolarProfile` (how much sun the world gets) which `DayNightStrategy`
turns into light and `WeatherStrategy` uses to shape its climate.

```text
Calendar ──> SeasonStrategy ── SolarProfile ──┐
    │        DayNightStrategy ───────────────┼─> Environment ──> ArcadeView
    └──────> WeatherStrategy ◄────────────────┘
```

### World and cells

The world is measured in **world units**. It is divided into square cells of
`WorldConfig.cell_size`:

```text
cols = round(width / cell_size)
rows = round(height / cell_size)
```

Defaults: `1200 x 800` world units, `cell_size=10` → `120 x 80 = 9600` cells.
Weather, light and readings are sampled per cell. The view applies one uniform
world→screen scale; it never assumes a pixel size for a cell.

---

## Configuration

Everything tunable lives in [`sim/config.py`](./sim/config.py) as dataclasses.
There is no YAML or JSON layer. `DEFAULT_CONFIG` is a `SimulationConfig` and is
the only object `main()` reads.

| Dataclass | Owns |
|-----------|------|
| `WorldConfig` | size, cell size, orientation, wrap |
| `TimeConfig` | ticks per day / season, start tick, initial/min/max playback scale |
| `BarrierConfig` | barrier colour (default yellow), max span cells, count, seed |
| `SeasonConfig` | one season: colours, gradient, climate baseline, sun intensity, daylight fraction, weather weights |
| `DayNightConfig` | sun/moon speeds, shading, thresholds, sky colours |
| `WeatherConfig` | field interval, seed, front count/radius/drift, condition effects |
| `EnvironmentConfig` | strategy class names + climate gradients + microclimate scale |
| `LoggingConfig` | level, format, business/readings switches |
| `SimulationConfig` | composes all of the above + `tick_rate` |

### Season count and names

Seasons are a list. One, two, four or eight seasons need no code change:

```python
from sim.config import SeasonConfig

DEFAULT_CONFIG.seasons = [
    SeasonConfig(
        name="Wet",
        ground_gradient=((40, 110, 90), (70, 150, 110)),
        base_temperature=22.0,
        temperature_swing=3.0,
        humidity=0.85,
        pressure_hpa=1006.0,
        sun_intensity=0.95,
        daylight_fraction=0.50,
        weather_weights={"clear": 15, "cloudy": 25, "rain": 50, "storm": 10, "snow": 0},
    ),
    SeasonConfig(
        name="Dry",
        ground_gradient=((190, 170, 90), (150, 120, 60)),
        base_temperature=30.0,
        temperature_swing=9.0,
        humidity=0.25,
        pressure_hpa=1018.0,
        sun_intensity=1.15,
        daylight_fraction=0.60,
        weather_weights={"clear": 70, "cloudy": 25, "rain": 5, "storm": 0, "snow": 0},
    ),
]
```

`SeasonStrategy.solar_profile(calendar)` blends the current season's
`sun_intensity` and `daylight_fraction` into the next season's over the final
quarter of the season, so the hand-off is continuous.

`SeasonStrategy.get_season_name(calendar)` is the interface point; alternate
season implementations may name or order seasons however they like.

### Positional gradients

Climate readings are not uniform. Each reading has a `GradientConfig`:

```python
@dataclass(frozen=True)
class GradientConfig:
    start: float = 0.0        # value at the "start" edge
    end: float = 1.0          # value at the "end" edge
    orientation: Optional[GradientOrientation] = None  # None inherits WorldConfig.orientation
```

Defaults in `DEFAULT_CONFIG.environment`:

| Reading | Gradient | Meaning |
|---------|----------|---------|
| Temperature | `GradientConfig(-4.0, 4.0)` | ±4 °C across the world |
| Humidity | `GradientConfig(-0.12, 0.12)` | ±12 % RH |
| Pressure | `GradientConfig(-6.0, 6.0)` | ±6 hPa |
| Light | `GradientConfig(0.88, 1.08)` | ±10 % multiplicative |

Supported orientations (members of `GradientOrientation`):

| Orientation | Direction |
|-------------|-----------|
| `NORTH_SOUTH` (`north_south`) | south → north |
| `SOUTH_NORTH` (`south_north`) | north → south |
| `WEST_EAST` (`west_east`) | west → east |
| `EAST_WEST` (`east_west`) | east → west |
| `CENTRE_OUT` (`centre_out`) | centre → edges/corners |
| `OUT_CENTRE` (`out_centre`) | edges/corners → centre |
| `DIAGONAL_UP` (`diagonal_up`) | south-west → north-east |
| `DIAGONAL_DOWN` (`diagonal_down`) | north-west → south-east |

Change the world-wide direction once:

Or override one reading independently:

```python
from sim.config import GradientConfig, GradientOrientation

DEFAULT_CONFIG.environment.temperature_gradient = GradientConfig(
    -6.0, 6.0, orientation=GradientOrientation.CENTRE_OUT
)
DEFAULT_CONFIG.environment.microclimate = 0.5   # damp the small sin/cos noise
```

Colour gradients use plain ``(start, end)`` tuples:

```python
SeasonConfig(
    name="Autumn",
    ground_gradient=((210, 170, 70), (150, 90, 40)),  # yellow -> rust
    ...
)
```

If `ground_gradient` is `None`, the ground colour falls back to
`ground_color` blended toward the next season.

### How a reading is composed

```text
light(x, y)       = sun_arc(season solar profile) * local_shading
                    * sun_intensity * light_gradient(x, y) * weather_light_factor
temperature(x, y) = season_base + swing * (2*light - 1)
                    + weather_temperature_offset
                    + temperature_gradient(x, y) + microclimate(x, y)
humidity(x, y)    = season_humidity + weather_humidity_offset
                    + humidity_gradient(x, y) + microclimate(x, y)
pressure(x, y)    = season_pressure + weather_pressure_offset
                    + pressure_gradient(x, y) + microclimate(x, y)
```

The season's `SolarProfile` (`sun_intensity`, `daylight_fraction`) drives the
day/night light curve; the day/night strategy no longer applies a
`light_influence` multiplier — that came from `SeasonConfig.light_influence`
and `DayNightConfig.season_light_influence`, both removed.

The per-condition offsets live in `WeatherConfig` (`temperature_offsets`,
`humidity_offsets`, `pressure_offsets`, `light_factors`) and default to
`WeatherConfig()` when no config is supplied.

### Weather field

```python
WeatherConfig(
    change_interval=600,        # 20 s at 30 ticks/s
    seed=1337,
    front_count=3,
    background_coverage=0.6,    # patchy background, never the whole grid
    front_radius_min_cells=2,
    front_radius_max_cells=6,
    front_drift_cells=0.0,
    background_patch_scale=1.0,
)
```

A new field is built every `change_interval` ticks, deterministically from
`(seed, interval, season)`. Each cell takes the most severe condition among:

1. the season-weighted **background** condition, where a deterministic patchy
   mask is below `background_coverage`;
2. every **front** whose radius covers the cell.

The strategy receives a `ClimateContext` (season, world geometry, temperature,
humidity, pressure, solar profile) and reshapes the season's weights with
`ClimateContext.adjusted_weather_weights()`: rain falls as snow below freezing,
storms need warmth and moisture, clear skies dominate dry air. Snow still only
appears in seasons whose `weather_weights` allow it.

Severity order: `clear < cloudy < rain = snow < storm`.

---

## Logging and instrumentation

Logging is configured before the container is built. Two streams are emitted:

- **operational** — startup, wiring, weather rebuilds, configuration fallbacks.
- **business** — what the player did and how the world reacted. Every entry is
  a single line: `event=<name> key=value ...`.

### Runtime level

Resolution order:

1. `BEAN_LOG_LEVEL` environment variable
2. `SimulationConfig.logging.level`
3. `INFO`

The Makefile exposes it as `LOG_LEVEL` (default `INFO`):

```bash
make run LOG_LEVEL=DEBUG
make verify LOG_LEVEL=DEBUG
BEAN_LOG_LEVEL=WARNING python -m sim.main
```

`LoggingConfig` also carries `format`, `date_format`, `business` and
`readings` / `readings_interval`. Reading samples are only emitted at `DEBUG`.

### Event catalogue

| Event | When | Notable fields |
|-------|------|----------------|
| `app.start` | process start | mode, world, cols/rows, level |
| `app.window_created` | windowed start | width, height |
| `app.window_closing` | exit requested | ticks, reason |
| `app.stop` | process end | ticks, state, reason |
| `container.built` | wiring done | world, cells, seasons, strategies |
| `session.started` | SPACE | key, tick, state |
| `session.paused` / `session.resumed` | P | key, tick |
| `session.restart` | SPACE on END | previous reason |
| `session.quit` / `session.closed` | Q/Esc | reason |
| `environment.day_changed` | day boundary | day, season, clock, year |
| `environment.season_changed` | season boundary | previous, season, day, year |
| `environment.weather_changed` | aggregate condition changed | previous, weather, season |
| `environment.reading` | DEBUG sample | temperature, humidity, pressure, light, gradient position |
| `weather.field_rebuilt` | every interval | base, coverage, front count, radius range |
| `weather.front` | DEBUG | index, kind, position, radius |
| `season.palette` | DEBUG | season, progress, ground colour, sun intensity, daylight fraction |
| `ui.cell_inspected` | click | cell, x/y, weather, temperature, humidity, pressure, light |
| `barrier.generated` | wiring | count, max_span_cells, color |
| `session.time_scale` | slider | scale |

Example (`LOG_LEVEL=DEBUG`):

```text
10:36:43 INFO    bean.environment | event=environment.season_changed day=5 previous=Spring season=Summer ticks_per_season=4800 year=1
10:36:43 DEBUG   bean.weather | weather.front index=1 kind=storm col=17.62 row=3.77 radius=5.93
10:36:43 DEBUG   bean.environment | event=environment.reading clock=01:12 day=1 gradient_position=0.5 humidity=0.494 light=0.023 phase=night pressure=1017.3 season=Spring temperature=8.2 tick=60 weather=cloudy
```

---

## Rendering

`ArcadeView` extends `arcade.Window` and implements `IRenderer`.

- **Layout** — a fixed left sidebar (`300..360 px`) holds stacked boxes: Time,
  Day, Season, Environment, Inspector, Weather field, Controls. The world uses
  the full height on the right and never sits under a box.
- **WorldLayout** — a single layout object (`sim/rendering/layout.py`) owns the
  world → screen projection and the cell grid. Both drawing (grid, cells,
  markers, barriers) and hit-testing (mouse motion/press) use this one layout,
  so the selected cell, the orange marker and the cursor always agree. Cell
  rectangles are integer-snapped so they land on whole pixels.
- **Day and season bars are separate** boxes, not a joined bar.
- **Inspector** — click a cell to pin it. The orange outline and the readings
  use the same integer cell index, so they always agree. A crosshair marks the
  cell centre.
- **Grid** — one line per cell boundary, derived from `world.cell_size` and
  `world.cols` / `world.rows`. The drawn world spans `cols*cell_size` by
  `rows*cell_size`, so lines always land on cell edges. Cells are drawn in
  screen units that honour `cell_size`, ready for beans to be drawn per cell.
- **Barriers** — drawn as filled cell-aligned rectangles in the barrier
  strategy's colour (default yellow), with a dark outline.
- **Playback-speed slider** — in the Controls box. Drag to slow / speed the
  perceived ticker; it sets `GameClock.time_scale` (clamped to
  `time_scale_min`/`time_scale_max`) and never changes `tick_rate` or
  sim-time progression. The initial value comes from
  `TimeConfig.initial_time_scale`.
- **Text** — all text uses cached `arcade.Text` objects. `arcade.draw_text` is
  never called; it is extremely slow and emits a `PerformanceWarning`.
- **Pointer mapping** — screen layout uses the active viewport size and mouse
  coordinates are scaled from the window size, so clicks line up on HiDPI or
  scaled displays. Layout is recomputed when the viewport changes.

The default window is sized for 1:1 world rendering (1 world unit = 1 screen
pixel) plus the sidebar, so the grid is crisp at startup.

The weather field box shows the live census (cells and percentage per
condition); rows are limited to the panel height and overflow is summarised as
`+N more conditions`.

---

## Containers

`Containerfile` builds a Python 3.10 image with Arcade and the application
source. Containers default to `BEAN_HEADLESS=1`.

```bash
make build
make run                         # detached headless
make logs                        # follow
make status
make stop
DISPLAY=:0 make run-container-ui # needs the host X11 socket
```

`make verify` is the developer-friendly check: it builds the image, runs a
bounded headless session in the foreground and exits with the container's
status.

---

## Verification

```bash
python3 -m compileall sim        # syntax
make test                        # compile + bounded headless locally
make verify LOG_LEVEL=DEBUG      # compile + headless in the container
make run-local                   # windowed smoke test
```

Expected headless invariants:

- day/season transitions are logged at the configured tick boundaries;
- `environment.weather_changed` and `weather.field_rebuilt` occur every
  `change_interval` ticks;
- `environment.reading` appears at `DEBUG`;
- two distant cells report different temperature/humidity/pressure values;
- no `PerformanceWarning` from Arcade.

---

## Documentation map

| File | Purpose |
|------|---------|
| [`README.md`](./README.md) | Current technical reference and usage (this file) |
| [`diagrams.md`](./diagrams.md) | Mermaid class, sequence, flow and state diagrams |
| [`spec.md`](./spec.md) | Original project specification, kept aligned with the code |
| [`AGENTS.md`](./AGENTS.md) | Documentation index for agents |
| [`CLAUDE.md`](./CLAUDE.md) | Behaviour and ground rules |
| [`skills/git.md`](./skills/git.md) | Local git workflow used by agents |
| [`TODO.md`](./TODO.md) | Task board for the current change set |

---

## Known limitations

- Beans ARE implemented: `DEFAULT_CONFIG` spawns ~1300 beans via the spawn
  controller (poisson_disc placement, average density, 50/50 male/female).
  Beans are drawn as small crosses in their gender color. Bean movement,
  collision and lifecycle systems are not yet implemented; the systems hook in
  `main.py` is a placeholder.
- Weather fronts are rebuilt from a seed every interval; `front_drift_cells`
  can move them between rebuilds but they do not animate continuously within an
  interval.
- The headless loop starts the session directly because there is no input to
  press `SPACE`.
- Automated tests and lint/typecheck configuration.
