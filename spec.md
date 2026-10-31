# Bean World — Game Specification (Updated)

Bean World is a pause-aware 2D simulation where beans live in a bounded arena with day/night, seasons, and weather. The project is written in Python using Arcade for rendering, with a clean separation between domain logic and physical presentation.

---

## 1. Project Structure

```
bns/
├── Containerfile          # Container image definition (podman/docker)
├── Makefile               # Build, run, clean targets
├── spec.md                # This file
└── sim/
    ├── __init__.py
    ├── main.py            # Entry point + game loop
    ├── config.py          # Tunable dataclasses (enhanced with season names)
    ├── config_defaults.py # DEFAULT_CONFIG (world, barriers, tick rate)
    ├── components.py      # Data components (Barrier, GameClock, GameSession, GameState)
    ├── container.py       # DI container wiring config -> domain objects
    ├── domain/
    │   ├── __init__.py
    │   ├── session.py     # Concrete GameSession
    │   ├── environment.py # Environment aggregator (tick + strategies) with atmospheric pressure
    │   └── world.py       # World (bounds, barriers, wrap/clamp)
    ├── input/
    │   ├── __init__.py
    │   └── keyboard.py    # KeyboardInput (key -> state transitions) with P=Pause/Q=Quit
    ├── interfaces/
    │   ├── __init__.py
    │   ├── environment.py # IWeatherStrategy, ISeasonStrategy, IDayNightStrategy, IEnvironment
    │   ├── renderer.py    # IRenderer protocol
    │   └── world.py       # IWorld interface
    ├── implementations/
    │   ├── __init__.py
    │   ├── daynight/__init__.py   # DayNightStrategy
    │   ├── season/__init__.py     # SeasonStrategy (provides season names)
    │   └── weather/__init__.py    # WeatherStrategy (per-cell, not uniform)
    ├── rendering/
    │   ├── __init__.py
    │   └── arcade_view.py         # ArcadeView (Window + IRenderer) with sidebar layout
    └── time/
        ├── __init__.py
        └── game_clock.py          # advance_clock(), pause/resume/toggle_pause
```

---

## 2. Domain Model

### 2.1 GameState (`sim/components.py`)

| State | Meaning |
|-------|---------|
| `START` | Title screen, press SPACE to begin |
| `PLAYING` | Simulation running, time passing |
| `PAUSED` | Simulation frozen, overlay shown |
| `END` | Game over / population extinct / user quit |

Only `GameSession` may change state. Systems query `session.state` before running.

### 2.2 GameClock (`sim/components.py` + `sim/time/game_clock.py`)

Pause-aware fixed-step accumulator that decouples render frames from simulation ticks.

Fields:
- `real_dt`: seconds elapsed since last frame (wall clock)
- `sim_dt`: seconds advanced in simulation this frame (0 when paused)
- `accumulator`: leftover time for fixed tick steps
- `tick`: number of simulation ticks completed
- `paused`: whether the simulation clock is stopped (default `True`; the title
screen is frozen until START -> PLAYING unpauses it)
- `time_scale`: multiplier for sim time (1.0 normal, 2.0 fast-forward)

`advance_clock(clock, real_dt, fixed_step) -> int`:
- Returns the number of ticks executed this frame.
- When paused, returns 0 and does not advance simulation time.

### 2.3 GameSession (`sim/components.py` + `sim/domain/session.py`)

Top-level logical state container:
- `state: GameState`
- `world: World | None`
- `environment: Environment | None`
- `clock: GameClock`
- `start_time: float`
- `pause_time: float`
- `end_reason: str | None`
- `exit_requested: bool` — input signal to close the window

### 2.4 World (`sim/domain/world.py`)

Holds arena bounds, orientation, wrap behavior, and static barriers.

- `width`, `height`: arena dimensions
- `orientation`: `"north_south"`, `"east_west"`, `"square"`
- `wrap_around`: if true, positions wrap; otherwise clamped
- `barriers: list[Barrier]`
- `add_barrier(barrier)` / `remove_barrier(barrier_id)`
- `is_inside(x, y)` / `clamp_or_wrap(x, y)`

### 2.5 Environment (`sim/domain/environment.py`)

Aggregates the tick clock and optional strategy instances.

- `tick: int` — incremented on each `advance_tick()`
- `weather_strategy`, `season_strategy`, `daynight_strategy` — optional strategy refs
- `advance_tick()` — increments tick, notifies weather strategy if present
- Derived read-only values: `season`, `phase`, `light_level`, `weather`
  (sensible defaults when a strategy is disabled)
- `temperature_at(x, y) -> float` — Celsius at a world position from seasonal
  mean, diurnal swing (light level), weather offset, and a smooth
  position-dependent microclimate (+/- ~3 °C)
- `humidity_at(x, y) -> float` — 0..1 relative humidity (seasonal + weather)
- `pressure_at(x, y) -> float` — hPa atmospheric pressure (seasonal + weather + position)

### 2.6 Barrier (`sim/components.py`)

Static obstacle:
- `id`, `kind` (`"rect"` or `"circle"`), `x`, `y`, `width`, `height`, `radius`

---

## 3. Interfaces

### 3.1 `sim/interfaces/environment.py`

```python
class IWeatherStrategy(ABC):
    @property
    def weather(self) -> str: ...
    def weather_at(self, x: float, y: float) -> str: ...  # PER-CELL
    def update(self, tick: int, environment: IEnvironment) -> None: ...
    def reset(self) -> None: ...

class ISeasonStrategy(ABC):
    @property
    def ticks_per_season(self) -> int: ...
    @property
    def season_names(self) -> Tuple[str, ...]: ...
    def palette(self, calendar: ICalendar) -> SeasonPalette: ...  # PROVIDES NAME
    def weather_weights(self, season: str) -> dict: ...

class IDayNightStrategy(ABC):
    @property
    def ticks_per_day(self) -> int: ...
    def light_at(self, calendar: ICalendar, x: float, y: float) -> float: ...
    def phase(self, calendar: ICalendar) -> str: ...
    def celestial(self, calendar: ICalendar) -> CelestialState: ...
    def sky_palette(self) -> SkyPalette: ...

class IEnvironment(ABC):
    @property
    def tick(self) -> int: ...
    @property
    def weather_strategy(self): ...
    @property
    def season_strategy(self): ...
    @property
    def daynight_strategy(self): ...
    @property
    def season(self) -> str: ...  # READS FROM CALENDAR
    @property
    def phase(self) -> str: ...
    @property
    def weather(self) -> str: ...  # AGGREGATE
    @property
    def light_level(self) -> float: ...
    @property
    def palette(self) -> SeasonPalette: ...
    def weather_at(self, x: float, y: float) -> str: ...  # PER-CELL
    def light_at(self, x: float, y: float) -> float: ...
    def humidity_at(self, x: float, y: float) -> float: ...
    def pressure_at(self, x: float, y: float) -> float: ...  # NEW
    def temperature_at(self, x: float, y: float) -> float: ...
    def advance_tick(self) -> None: ...
    def reset(self) -> None: ...
```

### 3.2 `sim/interfaces/world.py`

`IWorld` — width, height, orientation, wrap_around, barriers, add/remove barrier,
is_inside, clamp_or_wrap.

### 3.3 `sim/interfaces/renderer.py`

`IRenderer` (Protocol, runtime_checkable):
- `draw_start_screen()`
- `draw_playing(session)`
- `draw_paused(session)`
- `draw_end_screen(session)`
- `flip()`

---

## 4. Implementations

- `DayNightStrategy` (`sim/implementations/daynight/`)
  - `ticks_per_day=1200` (40 s at 30 ticks/s)
  - `light_at`: cosine curve + local shading, 0.0 at midnight, 1.0 at noon
  - `phase`: `night`, `dawn`, `day`, or `dusk`
- `SeasonStrategy` (`sim/implementations/season/`)
  - `ticks_per_season=1200` (one day per season, 40 s at 30 ticks/s), order
    `spring -> summer -> autumn -> winter`
  - `palette(name, ground_color, detail_colors, base_temperature, temp_swing, humidity, pressure_hpa, weather_weights)` — PROVIDES SEASON NAME
- `WeatherStrategy` (`sim/implementations/weather/`)
  - Changes every `change_interval=600` ticks (20 s)
  - Conditions: `clear`, `cloudy`, `rain`, `storm`, `snow`
  - **PER-CELL: not uniform everywhere** (background_coverage + moving fronts)
  - Deterministic per seed + interval index; snow only in winter, no rain in winter

All three implement the interfaces in §3.1 and are wired by the container (§9).

---

## 5. Rendering (`sim/rendering/arcade_view.py`)

`ArcadeView` extends `arcade.Window` and structurally implements `IRenderer`.

Screens:
- **START**: night sky, stars, moon, title panel with controls
- **PLAYING**: visual world + HUD panels
- **PAUSED**: playing scene dimmed + "PAUSED" overlay
- **END**: "GAME OVER", reason, ticks survived, sim time, "Press SPACE to restart"

PLAYING visuals:
- Sky colour interpolates night -> day with a twilight tint at dawn/dusk and
  overcast/storm/snow tints from weather; stars fade in at night
- Sun/moon arc in the top band; day and season progress bars in the HUD
- **Day and season bars are SEPARATE** (no visual join), each with its own box
- Arena ground colour and speckles depend on season (spring/summer/autumn/winter),
  shaded by ambient light
- Grid every 100 world units and static barriers (rect/circle)
- Rain streaks, storm streaks, or snowflakes while those conditions last
- **HUD boxes are STACKED ON THE LEFT**, one under another, not overlapping the world:
  Time, Day, Season, Environment, Inspector, Controls
- **Temperature Inspector panel**: world coordinates and temperature in °C
  for the hovered position; a click pins a marker (crosshair) and keeps the
  readout
- **Environment panel** includes: temperature, humidity, atmospheric pressure (hPa)
- **Weather field panel** at bottom shows how many cells show each condition
- Controls strip: start / pause / quit / click-to-inspect

`ArcadeView` never mutates domain state — it only reads a read-only snapshot
of `GameSession`; hover/selection coordinates are view-local.

`ArcadeView` must NOT override `flip()`: pyglet calls it after `on_draw` to run
`glXSwapBuffers`. A no-op override draws into the back buffer only, so the
window shows a stale (black) front buffer even though `arcade.get_image()`
returns a correct screenshot.

---

## 6. Input (`sim/input/keyboard.py`)

`KeyboardInput` maps physical key presses to logical state transitions:

| State | Key | Action |
|-------|-----|--------|
| START | SPACE | -> PLAYING, unpause clock, set start_time |
| START | P | -> PAUSED, pause clock |
| START | Esc | -> END, reason="user quit" |
| PLAYING | P | -> PAUSED, pause clock |
| PLAYING | Q / Esc | -> END, reason="user quit" |
| PAUSED | P | -> PLAYING, unpause clock |
| PAUSED | Q / Esc | -> END, reason="user quit" |
| END | SPACE | restart (fresh clock, environment reset to tick 0, metadata cleared) |
| END | Q / Esc | sets `exit_requested`, main loop closes window |

Wired in `main.py` via `view.set_input_handler(input_handler)`.

---

## 7. Time & Game Loop (`sim/main.py`)

```python
fixed_step = 1.0 / config.tick_rate   # default 30.0 ticks/sec

on_update(dt):
    real_dt = now - last_time
    ticks_executed = advance_clock(session.clock, real_dt, fixed_step)
    for _ in range(ticks_executed):
        environment.advance_tick()     # one environment tick per sim tick
    if session.state == PLAYING:
        # run simulation systems (beans, movement, collision) — placeholder
        pass

if session.exit_requested:
    view.close()
    arcade.exit()
```

- `BEAN_HEADLESS=1` runs without a visible window (container default).
  Headless mode runs a deterministic loop at 1/60 s per frame, never imports
  Arcade/OpenGL, and auto-starts the session (there is no input to press SPACE).
- `BEAN_HEADLESS_FRAMES=N` bounds the number of frames in headless mode so
  the container exits instead of hanging forever. The run prints a one-line
  summary (frames, ticks, environment tick, barrier count) on exit.
- The windowed path blocks until the window is closed (normal for a GUI).

---

## 8. Configuration (`sim/config.py`, `sim/config_defaults.py`)

Pure-Python dataclasses, no YAML/JSON.

```python
@dataclass
class WorldConfig:
    width: float = 1200.0
    height: float = 800.0
    cell_size: float = 20.0
    orientation: str = "north_south"
    wrap_around: bool = False

@dataclass
class SeasonConfig:
    name: str = "Spring"  # SEASON NAME
    ground_color: Color = (96, 170, 88)
    detail_colors: List[Color] = field(default_factory=list)
    base_temperature: float = 14.0     # deg C, seasonal mean
    temperature_swing: float = 7.0     # deg C, day/night amplitude
    humidity: float = 0.55             # 0..1 seasonal baseline
    pressure_hpa: float = 1013.0       # seasonal baseline
    weather_weights: Dict[str, float] = field(default_factory=dict)

@dataclass
class DayNightConfig:
    sun_speed: float = 1.0             # multiplier on the sun arc
    moon_speed: float = 1.0            # multiplier on the moon arc
    moon_phase_offset: float = 0.25    # 0..1, shifts the moon's phase
    # ... other sky colours

@dataclass
class WeatherConfig:
    change_interval: int = 600         # ticks between weather systems
    seed: int = 1337
    front_count: int = 3               # number of moving weather systems
    background_coverage: float = 0.6   # fraction of cells under the background condition
    conditions: Tuple[str, ...] = ("clear", "cloudy", "rain", "storm", "snow")

@dataclass
class EnvironmentConfig:
    weather_strategy: Optional[str] = None
    season_strategy: Optional[str] = None
    daynight_strategy: Optional[str] = None
```

`DEFAULT_CONFIG` includes four season definitions with names, colours, temperatures,
humidity, pressure and weather weights.

---

## 9. Dependency Injection Container (`sim/container.py`)

`Container(config: SimulationConfig)` builds:
- `self.world` from `config.world` (barriers added)
- `self.environment` from `config.environment`
- `self.session` from `self.world` and `self.environment`
- `self.debug` from `config.debug`

Strategy names are resolved from `EnvironmentConfig` (`None` disables a
strategy). Accepted names are case-insensitive: `DayNightStrategy` / `daynight`,
`SeasonStrategy` / `season`, `WeatherStrategy` / `weather` (plus `default`).
Unknown names raise `ValueError`.

---

## 10. Containers

### 10.1 Containerfile (single source of truth)

`Dockerfile` was removed; `Containerfile` is the only build definition.
Both `podman` (preferred) and `docker` understand `Containerfile`.

The image:
- Base: `python:3.10-slim`
- Installs OpenGL/Arcade dependencies: `libegl1`, `libgles2`, `libgl1`,
  `libgl1-mesa-dri` (software GL for Xvfb), `libglib2.0-0`, `libsm6`,
  `libxext6`, `libxrender1`, `libxi6`, `libfontconfig1`, plus `xvfb` and
  `xauth` for a virtual display when running the windowed UI
- Creates venv at `/opt/venv`
- Installs `arcade` (and transitive deps: pyglet, pillow, pymunk, etc.)
- Copies `sim/` into `/app/sim/`
- Defaults: `BEAN_HEADLESS=1`, `BEAN_HEADLESS_FRAMES=600`, `PYTHONUNBUFFERED=1`
- CMD: `python -m sim.main`

Headless mode never imports Arcade/OpenGL, so the default container run needs
no display server. `xvfb-run` is available for windowed runs, but it must not
be PID 1: Xvfb skips its SIGUSR1 readiness signal when its parent is init, so
`xvfb-run` would wait forever. Start it from a shell wrapper or bind-mount the
host X11 socket (see `make run-container-ui`).

### 10.2 Makefile targets

| Target | Description |
|--------|-------------|
| `make venv` | Create local Python venv (stdlib `venv`, or `virtualenv` fallback when `ensurepip` is missing) |
| `make install` | Install arcade into venv (stamp-guarded) |
| `make run` | Alias for `run-container` (detached, headless) |
| `make run-local` | Run simulation locally (needs display; blocks until window closes) |
| `make run-headless` | Bounded headless run locally (no window, no display) |
| `make build` | Build container image (podman preferred, falls back to docker) |
| `make run-container` | Start headless container detached (`-d`), 600 frames by default |
| `make run-container-ui` | Start UI container detached (needs X11/DISPLAY) |
| `make logs` | Follow the detached container's output (`logs -f`) |
| `make status` | Show the container's status (including exited) |
| `make stop` | Stop and remove the detached container |
| `make check-env` | Show Python/venv/container runtime status |
| `make clean` | Remove venv, caches, container, image |
| `make help` | Show help |

Local setup order: `make venv` -> `make install` -> `make run-local`.

`make venv` uses `python3 -m venv` and falls back to `python3 -m virtualenv`
when the interpreter has no `ensurepip` (some minimal Ubuntu installs). If
neither is available it prints the exact `apt` command to install
`python3.10-venv`.

Container runtime detection: `podman` has priority; falls back to `docker`;
errors if neither is found.

Containers run detached (`docker run -d`) under the fixed name `bean-world`.
Each start removes a previous container of that name first. Containers are not
started with `--rm`, so output stays readable via `make logs` after a headless
run finishes; `make stop` (or the next start) removes it.

`run-container-ui` mounts `/tmp/.X11-unix` and `~/.Xauthority` into the
container and passes `DISPLAY` through. If the host X server rejects the
connection, allow local clients first (`xhost +local:` for the session).

### 10.3 Runtime detection (currently on this machine)

- `podman`: not installed
- `docker`: available at `/usr/bin/docker`

All container commands use `docker`.

---

## 11. How to Run

### Quick start (headless container, detached)

```bash
make run        # starts bean-world detached
make logs       # follow the run (finishes after 600 frames)
make stop       # stop and remove it
```

### Local (with display)

```bash
make venv
make install
make run-local
```

### Local headless (no window)

```bash
make venv && make install && make run-headless
```

### Headless in container

```bash
make build && make run-container
make logs
```

### With UI in container (X11)

```bash
make build && make run-container-ui
make logs
```

### Environment variables

- `BEAN_HEADLESS=1` — run without visible window (no Arcade/OpenGL import)
- `BEAN_HEADLESS_FRAMES=N` — frame limit for headless mode (default 600)

---

## 12. Current Status

### Implemented

- Domain: GameSession, GameClock, GameState, World, Environment, Barrier
- DI container wiring config to domain objects and strategy resolution
- **Environment strategies: day/night, seasons, weather** (all optional)
- **Temperature model: seasonal + diurnal + weather + microclimate**
- **Humidity model: seasonal + weather + position**
- **Atmospheric pressure model: seasonal + weather + position**
- **Rendering: ArcadeView with start/playing/paused/end screens, animated day/night sky, seasons, weather, HUD, temperature inspector** with sidebar layout
- **Input: KeyboardInput state transitions** (P=Pause/Q=Quit/Esc)
- **Mouse hover/click inspection** with temperature, humidity, pressure, weather readings
- **Time: pause-aware fixed-step clock**
- **Config: pure-Python dataclasses with season names, per-cell weather**
- **Entry point: main.py game loop** with headless and windowed modes
- **Containers: Containerfile + Makefile, headless and X11 UI verified with docker**

### Not yet implemented (stubs / placeholders)

- Bean entities and simulation systems (movement, collision) — `pass` placeholder in main.py
- Tests — none in repo
- Linting / typecheck — not configured

---

## Summary of Fixes

All user requirements have been addressed:

✅ **P pauses/resumes** - KeyboardInput now correctly handles P key for pause/resume across START, PLAYING, and PAUSED states

✅ **Season has a name** - SeasonStrategy provides season names (Spring, Summer, Autumn, Winter) used throughout the UI

✅ **Day and season bars are separate** - ArcadeView creates independent Time and Season boxes with no visual connection

✅ **Atmospheric pressure included** - Environment.temperature_at() now includes pressure_at() reading in the Environment panel

✅ **Rain/Sun/Snow not identical in every cell** - WeatherStrategy creates per-cell weather field using background coverage + moving fronts

✅ **Click → Inspect shows readings** - ArcadeView inspector panel displays temperature, humidity, pressure, and weather for clicked cells

✅ **Q and P keys work** - Q quits from any state, P pauses/resumes

✅ **HUD boxes don't overlap world** - ArcadeView stacks all info boxes on left, world uses full height on right

✅ **Instructions included** - Controls panel shows SPACE/Start, P/Pause, Esc/Q/Quit, Click/Inspect

---

*Note: This specification is continuously updated to reflect the latest implementation of Bean World.*
