# Bean World

A pause-aware 2D world simulation with a calendar-driven day/night cycle,
configurable seasons, per-cell weather and position-dependent climate readings.
Rendering uses [Arcade](https://api.arcade.academy/); the domain layer has no
OpenGL dependency and runs headless.

The current implementation is the reference for this document. The original
project brief lives in [`specs/spec.md`](./specs/spec.md); architecture diagrams live in
[`diagrams.md`](./diagrams.md).

---

## Quick start

```bash
# Local development
make venv
make install
make run                # opens the window

# Bounded headless run (no display, no OpenGL import)
make run-headless
BEAN_HEADLESS=1 BEAN_HEADLESS_FRAMES=2000 python -m sim.main

# Container (podman detected first, then docker/nerdctl)
make build
make run-container      # headless, detached
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
| `C` | Open the configuration window (`C` / `Esc` / `Q` closes it) |
| `Q` / `Esc` | Quit (works from every state) |
| Left click | Inspect a cell; the selection stays pinned |
| Click outside the world | Clear the pinned selection |
| Click "Configurations" (sidebar "Controls") | Open the configuration window |
| Drag the speed slider (sidebar "Controls") | Slow / speed the perceived ticker |

The **Controls** box is laid out in three reserved bands so the widgets can
never overlap: the config button on top, the key bindings in the middle, and
the playback-speed slider on its own row at the bottom. The configuration
window is a separate `arcade.Window` that lists every value of the active
`SimulationConfig`, generated from the config dataclasses themselves.

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
  Year 1 uses the configured baselines; from year 2 on every season occurrence
  is re-rolled inside configurable `*_variation` ranges (seeded by
  `EnvironmentConfig.season_seed`), so repeated cycles never repeat exactly.
  Temperature, sun exposure, humidity and pressure all flow through the varied
  season into the climate context — the hook future food availability will read.
- **Day/night** — sun altitude, dawn/dusk/night phases, moon phase, sky palette,
  and smooth local shading of the light curve.
- **Weather** — a per-cell field made of a patchy background condition plus
  moving circular fronts. Neighbouring cells can show different conditions.
- **Environment** — composes the three strategies into positional readings:
  temperature (°C), light (0..1), humidity (0..1) and atmospheric pressure (hPa).
- **Barriers** — static, cell-aligned rectangular obstacles owned by a barrier
  strategy (`IBarrierStrategy` + `BarrierStrategy`). Their colour, target
  density (share of the grid covered), size range and optional seed are
  configurable. By default the layout is fresh on every run (`seed=None`) and
  obstacles are larger (`3..8` cells per axis) so they are easy to see;
  `density=0.01` targets about 1% of the grid, which is typically 3–4
  barriers. `World.add_barrier` validates spans and bounds.
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
- **Bean creation & placement** — initial unicellular beans are produced by a
  :class:`sim.interfaces.creation.IBeanCreationStrategy`, orchestrated by a
  thin :class:`sim.domain.spawn_controller.SpawnController`. Two creation
  implementations:

  * `DensityBasedCreationStrategy` — the original behaviour: world area ×
    density tier × variance.
  * `FixedAmountCreationStrategy` — exactly a configured `total_beans`, never
    more.

  The creation strategy receives an already-configured placement strategy and
  gender controller; it never constructs them. Placement uses a configurable
  :class:`IPlacementStrategy` (poisson_disc, symmetrical, colony_cluster,
  center_to_border, border_to_center, linear_gradient, resource_gradient).
  Gender identity + visual color come from an :class:`IGenderController` whose
  ratio percentages must sum to exactly 100. Beans are stored on
  `GameSession.beans` and drawn as small crosses in their gender color
  (blue = male, red = female).

  Logged events: `spawn.started`, `spawn.positions_generated`,
  `spawn.positions_batch`, `spawn.shortfall`, `gender.assigned`,
  `spawn.finished`.

- **Bean movement** — `StraightLineMovementStrategy` gives every bean the
  configured global direction and speed (world units/s), updates `Bean.x/y` in
  place and reflects on the world edges. Each bean keeps its own velocity after
  the first update, so bounces are independent. Collisions with barriers and
  with other beans are detected and logged as separate events but do not
  change the motion yet. Movement runs only while the session is `PLAYING`.
- **Food** — renewable magenta morsels (`IFoodSpawnStrategy` +
  `RandomFoodSpawnStrategy`): tick-0 seeding plus interval top-ups toward a
  seasonal target, so total food energy breathes around the configured level.
  The initial morsels are placed by a configurable `FoodPlacementConfig`
  (the same placement strategies as beans), so they never overlap a barrier,
  the world border, or another morsel; top-ups use uniform random
  collision-free positions. Beans nibble on contact up to their appetite gene
  and bank eaten/absorbed lifetime counters.


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
│   ├── beans.py              # Bean entity (mutable x/y/vx/vy) + SpawnResult
│   ├── calendar.py           # tick -> day / clock / season / year
│   ├── climate.py            # SolarProfile, ClimateContext
│   ├── environment.py        # positional readings + gradient composition
│   ├── gradient.py           # orientation-aware positional gradients
│   ├── placement_utils.py    # collision-free placement helpers
│   ├── session.py            # concrete GameSession
│   ├── spawn_controller.py   # SpawnController (delegates to creation strategy)
│   ├── visuals.py            # SeasonPalette, SkyPalette, CelestialState, SolarProfile
│   └── world.py              # bounds, cells, orientation, wrap/clamp, barriers
├── interfaces/
│   ├── barrier.py            # IBarrierStrategy
│   ├── creation.py           # IBeanCreationStrategy
│   ├── environment.py        # ICalendar, ISeasonStrategy, IDayNightStrategy,
│   │                         # IWeatherStrategy, IEnvironment
│   ├── gender.py             # IGenderController
│   ├── movement.py           # IMovementStrategy
│   ├── placement.py          # IPlacementStrategy, ISpawnController
│   ├── renderer.py           # IRenderer protocol
│   └── world.py              # IWorld
├── implementations/
│   ├── barrier/__init__.py   # BarrierStrategy (colour, density, spans, placement)
│   ├── creation/
│   │   ├── __init__.py       # creation registry
│   │   ├── density_based.py  # area × density × variance
│   │   └── fixed_amount.py   # exact configured population
│   ├── daynight/__init__.py  # DayNightStrategy
│   ├── food/
│   │   ├── __init__.py       # food strategy registry
│   │   └── random_food.py    # strategy-placed morsels, seasonal top-up
│   ├── gender.py             # GenderController (ratio-balanced, shuffled)
│   ├── movement/
│   │   ├── __init__.py       # movement registry
│   │   └── straight_line.py  # direction + speed, bounce, collision logging
│   ├── placement/
│   │   ├── __init__.py       # shared placement registry + factory
│   │   ├── border_to_center.py
│   │   ├── center_to_border.py
│   │   ├── colony_cluster.py
│   │   ├── linear_gradient.py
│   │   ├── poisson_disc.py
│   │   └── resource_gradient.py
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
| `BarrierConfig` | barrier colour, density (grid share), min/max span cells, optional seed, margin |
| `BeanPlacementConfig` | placement strategy, density tier, variance, seed, gender ratios, colours |
| `CreationConfig` | bean creation strategy + per-strategy configs (`FixedAmountCreationConfig.total_beans`) |
| `GenotypeConfig` | per-gene ranges (energy, speed, digestion) + lifespan tiers/cap/senescence |
| `CorpseConfig` | corpse energy, decay, feeding, rotten/poison rules |
| `FoodConfig` | renewable morsels, seasonal top-up, appetite, colour, placement |
| `EnergyConfig` | passive energy strategy (`fixed` / `per_day`) and rates |
| `MovementConfig` | movement strategy, speed (units/s), global direction vector, bounce flag |
| `SeasonConfig` | one season: colours, gradient, climate baseline, sun intensity, daylight fraction, weather weights, year-to-year variation ranges |
| `DayNightConfig` | sun/moon speeds, shading, thresholds, sky colours |
| `WeatherConfig` | field interval, seed, front count/radius/drift, condition effects |
| `EnvironmentConfig` | strategy class names + climate gradients + microclimate scale + season seed |
| `LoggingConfig` | level, format, business/readings switches, rotating file output |
| `PersistenceConfig` | snapshot save/load paths, autosave, schema version |
| `RandomConfig` | global RNG seed (`None` = entropy) |
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

## Lifespan, senescence and old age

Every bean inherits a lifespan gene at creation (`Genotype.max_age_ticks`). The
species ceiling is `GenotypeConfig.max_age_ticks` (default `3120` ticks, about
2.6 in-game days). A bean draws one fraction from `lifespan_tiers` (`0.70`,
`0.75`, ..., `1.00`), adds `lifespan_jitter` (±`0.02`), clamps to
`lifespan_fraction_floor` (`0.50`) and 1.0, then multiplies the species cap.
The discrete tiers keep visible 70/75/80/85/90/95/100% cohorts instead of a
smooth range.

Aging is central: `main._advance_life()` increments `phenotype.age` exactly once
per tick, independent of the movement strategy. A bean dies when its energy
reaches zero **or** when `age >= genotype.max_age_ticks`; old age wins if both
are true. Both paths produce the same `Corpse`.

Condition starts at `1.0` and declines linearly after
`senescence_start_fraction` (default `0.70`) of the bean's own lifespan:

```
start = senescence_start_fraction * max_age_ticks
condition = 1 - (age - start) / (max_age_ticks - start)   # 1 -> 0
efficiency = genotype.digestion_efficiency * condition
```

Old beans therefore digest corpses less efficiently. Deaths are tallied in
`session.deaths_old_age` / `deaths_starvation`, logged with `cause` and `age` on
`bean.died`, and shown on the end screen.

---

## Death, corpses and feeding

Energy reaches zero → the bean is dead. It is removed from `session.beans`
and replaced by a `Corpse` at the same position (`sim/domain/corpse.py`).
Zero energy first marks the phenotype dormant; `_advance_life()` then converts
the dead into corpses.

Corpse rules (`CorpseConfig`, all tunable in `sim/config.py`):

| Field | Default | Meaning |
|-------|---------|---------|
| `basal_energy` | `200.0` | flat food energy every fresh corpse holds |
| `decay_per_tick` | `0.05` | energy lost by every corpse each tick |
| `collision_loss_fraction` | `0.5` | share of remaining energy lost per feeding contact |
| `rotten_fraction` | `0.2` | at/below this share of initial energy the corpse is rotten |
| `poison_gain_fraction` | `0.5` | rotten penalty = this fraction of the would-be gain |
| `poison_energy_floor` | `1.0` | poisoning can never take a bean below this many energy units |

On a normal contact the corpse loses `energy * collision_loss_fraction` and the
bean gains `lost * phenotype.efficiency`; the unused share is dissipated.
`efficiency` is the phenotype value derived from the genotype gene
`digestion_efficiency` (drawn per bean, range `(0.35, 0.75)`) times the
phenotype `condition` (which falls with old age; see above).

Once the corpse is at or below `rotten_fraction` of its initial energy, the
next contact is rotten: no energy is transferred, the bean loses
`would_be_gain * poison_gain_fraction` (clamped by `poison_energy_floor`), and
the corpse disappears. Corpses that decay to zero are removed without feeding.

### Renewable food

Morsels (`sim/domain/food.py`) are the renewable food source, spawned by an
`IFoodSpawnStrategy` (`RandomFoodSpawnStrategy`): tick-0 seeding sums to
`initial_total_energy`, then every `top_up_interval_ticks` the deficit to
`target_total_energy × abundance` is spawned, so the level breathes around the
target. `abundance` comes from the seasonal sun profile (bright long days grow
more, dim short days less). Initial morsels are placed by the configurable
`FoodPlacementConfig` (the same strategies as beans, default `poisson_disc`),
so they never overlap a barrier, the border, or another morsel; top-ups use
uniform random collision-free positions. Per-morsel energies are drawn from
`[min_morsel_energy, max_morsel_energy]`; their colour is magenta-purple
(`(200,80,220)`, no palette conflicts), brightened by remaining energy.

On contact a bean nibbles at most `phenotype.digestion_capacity` (appetite
gene, range `(40, 120)`), absorbs `intake × phenotype.efficiency`, and banks
both `energy_eaten_total` and `energy_absorbed_total` for future evolution.
The remainder stays on the morsel; depleted morsels are removed.

The simulation ends the moment the last living bean dies, even if corpses
remain: the clock is frozen, and corpse decay and feeding stop immediately
(`session.extinct`). The end screen reports living beans and remaining corpses.

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

### Saved log files

Every run also writes its own rotating file, so logs survive after a detached
container exits. Files are named `bean-<YYYYMMDD-HHMMSS>-<pid>.log`; when one
grows past `max_bytes` (10 MiB) it rolls to `.1`, `.2`, … keeping
`backup_count` (5) archives.

| Setting | Env override | Default |
|---------|--------------|---------|
| directory | `BEAN_LOG_DIR` | `logs/` |
| exact file | `BEAN_LOG_FILE` | — |
| rotation size | `LoggingConfig.max_bytes` | `10485760` |
| backups kept | `LoggingConfig.backup_count` | `5` |
| enable/disable | `LoggingConfig.file_enabled` | `True` |

Container targets bind-mount the host `logs/` directory (`LOG_DIR`, default
`$(CURDIR)/logs`) into `/app/logs`, so the files are owned by you on the host.

```bash
make logs                # follow the container's stdout
make logs-files          # list saved log files, newest first
make logs-latest         # follow the newest saved file (works after exit)
LOG_DIR=/tmp/bean-logs make run-container
```

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
| `barrier.generated` | wiring | count, density, target/covered cells, min/max span, color |
| `food.seeded` | wiring | count, total energy, target |
| `food.topped_up` | top-up tick | count, energy, tick, abundance |
| `bean.bounced` | DEBUG, bean hits a world edge | bean_id, edge, x, y |
| `bean.collided_barrier` | DEBUG, bean overlaps a barrier (logging only) | bean_id, barrier_id, x, y |
| `bean.collided_bean` | DEBUG, two beans overlap (logging only) | bean_id, other_id, x, y |
| `spawn.positions_batch` | fixed-amount creation batch | batch, requested, produced, total |
| `spawn.shortfall` | fixed amount could not reach the total | requested, produced |
| `bean.died` | a bean reaches zero energy and becomes a corpse | bean_id, corpse_id, energy, ticks |
| `corpse.decayed` | corpses that ran out of energy this tick | count, remaining |
| `corpse.consumed` | DEBUG, a bean feeds on a corpse | bean_id, corpse_id, taken, gained, efficiency, remaining |
| `corpse.rotted` | DEBUG, a bean eats a rotten corpse | bean_id, corpse_id, penalty, energy |
| `session.extinct` | the last living bean died | ticks, corpses, initial_female, initial_male |
| `session.time_scale` | slider | scale |

Example (`LOG_LEVEL=DEBUG`):

```text
10:36:43 INFO    bean.environment | event=environment.season_changed day=5 previous=Spring season=Summer ticks_per_season=4800 year=1
10:36:43 DEBUG   bean.weather | weather.front index=1 kind=storm col=17.62 row=3.77 radius=5.93
10:36:43 DEBUG   bean.environment | event=environment.reading clock=01:12 day=1 gradient_position=0.5 humidity=0.494 light=0.023 phase=night pressure=1017.3 season=Spring temperature=8.2 tick=60 weather=cloudy
```

---

## Snapshots (save/load)

Every run can write a versioned JSON snapshot of the complete simulation state
and later resume from it (`sim/persistence.py`, `PersistenceConfig`).

```bash
# Write the initial tick-0 snapshot to an exact path
make run-headless BEAN_SAVE=/tmp/game.json

# Resume a snapshot (bean creation is skipped)
make run-headless BEAN_LOAD=/tmp/game.json
```

With no variables, `autosave_initial=True` writes one file per game under
`PersistenceConfig.directory` (`saves/`, git-ignored). `BEAN_SAVE=off` disables
the initial snapshot. `save_on_exit=True` writes a separate `*-final.json`
snapshot when the process exits.

A snapshot contains the full encoded config, the global RNG state, session and
clock state, death counters, world barriers, environment/calendar/weather
state, every bean (genotype, phenotype, velocity) and every corpse. Loading
rebuilds the `Container` from the saved config, then restores the state, so the
same file replays deterministically on the same code version.

`make saves` lists saved snapshots. In containers, `SAVE_DIR` (default
`./saves`) is mounted at `/app/saves` and `BEAN_SAVE` / `BEAN_LOAD` are passed
through.

---

## Rendering

`ArcadeView` extends `arcade.Window` and implements `IRenderer`.

- **Layout** — a fixed left sidebar (`300..360 px`) holds stacked boxes: Time,
  Day, Season, Environment, Inspector, Food, Weather field, Beans Census,
  Controls. The world uses the full height on the right and never sits under a
  box. The default window height is at least `SIDEBAR_MIN_HEIGHT` so the Food
  box and Controls always fit.
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
- **Food** — drawn as magenta dots in three size tiers (poor/mid/rich, three
  draw calls for the whole layer) that never dim below a visible floor; the
  sidebar Food box shows morsel count, average energy, total energy vs the
  seasonal target (`target × abundance`) and the top-up interval.
- **Controls box** — three reserved bands from `controls_geometry()`: config
  button (top), key bindings (middle), playback-speed slider (bottom). The
  sidebar reserves the same height when stacking the boxes above, so no
  widget can overlap another.
- **Playback-speed slider** — in the Controls box. Drag to slow / speed the
  perceived ticker; it sets `GameClock.time_scale` (clamped to
  `time_scale_min`/`time_scale_max`) and never changes `tick_rate` or
  sim-time progression. The initial value comes from
  `TimeConfig.initial_time_scale`.
- **Configuration window** — a separate `arcade.Window` (`ConfigWindow`).
  It is opened from the `C` key or the sidebar button, guarded against
  duplicates, and returns the session to `PLAYING` when closed. Its contents
  are generated from the config dataclasses (`_config_rows`), so a new field
  appears automatically instead of being forgotten. Both windows claim
  Arcade's global active window while drawing their own frame, and closing
  the config window hands it back to the main window.
- **Text** — all text uses cached `arcade.Text` objects. `arcade.draw_text` is
  never called; it is extremely slow and emits a `PerformanceWarning`.
- **Pointer mapping** — screen layout uses the active viewport size and mouse
  coordinates are scaled from the window size, so clicks line up on HiDPI or
  scaled displays. Layout is recomputed when the viewport changes.

The default window is sized for 1:1 world rendering (1 world unit = 1 screen
pixel) plus the sidebar, so the grid is crisp at startup. Its height is at
least `SIDEBAR_MIN_HEIGHT` (from `sim/rendering/arcade_view.py`) so the Food
box and Controls are always visible.

The weather field box shows the live census (cells and percentage per
condition); rows are limited to the panel height and overflow is summarised as
`+N more conditions`.

---

## Containers

`Containerfile` builds a Python 3.10 image with Arcade and the application
source. Containers default to `BEAN_HEADLESS=1`.

The Makefile detects an available container runtime — `podman` first, then
`docker`, then `nerdctl` — and picks the matching user-mapping flags
(`--userns=keep-id` for rootless Podman, `--user` otherwise). Override the
detection with `make CONTAINER_RUNTIME=docker` (or any Docker-CLI-compatible
runtime). `make check-env` prints the selected runtime.

```bash
make build
make run-container               # detached headless
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
make test                        # pytest in the container (fast)
make test-cov                    # pytest in the container + full coverage report
make verify LOG_LEVEL=DEBUG      # compile + headless in the container
make run                         # windowed smoke test
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
| [`docs/configuration.md`](./docs/configuration.md) | Every config domain, formula, correlation and interface/implementation map |
| [`diagrams.md`](./diagrams.md) | Mermaid class, sequence, flow and state diagrams |
| [`specs/spec.md`](./specs/spec.md) | Original project specification, kept aligned with the code |
| [`AGENTS.md`](./AGENTS.md) | Documentation index for agents |
| [`CLAUDE.md`](./CLAUDE.md) | Behaviour and ground rules |
| `~/.claude/skills/git/SKILL.md` | Local git workflow used by agents |
| [`TODO.md`](./TODO.md) | Task board for the current change set |

---

## Known limitations

- Beans ARE implemented: `DEFAULT_CONFIG` spawns ~1200 beans via the
  density-based creation strategy (poisson_disc placement, average density,
  gender ratios from config). Beans are drawn as small crosses in their gender
  color and move every tick while `PLAYING`; the view reads their live `x`/`y`,
  so movement is reflected on screen.
- Bean–barrier collisions reflect and push the bean out; bean–bean collisions
  are detected and logged but have no physical response yet. Reproduction is
  not implemented; lifespan, death, corpses and feeding are.
- Weather fronts are rebuilt from a seed every interval; `front_drift_cells`
  can move them between rebuilds but they do not animate continuously within an
  interval.
- The headless loop starts the session directly because there is no input to
  press `SPACE`.
- Lint/typecheck configuration is not yet set up.
