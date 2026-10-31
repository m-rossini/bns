# Bean World — Diagrams

Mermaid diagrams of the current implementation. They are intentionally
code-accurate: names match `sim/` and the arrows follow real imports and calls.

- [Class diagram](#class-diagram)
- [Wiring sequence](#wiring-sequence)
- [Simulation tick sequence](#simulation-tick-sequence)
- [Reading composition](#reading-composition)
- [Render / input loop](#render--input-loop)
- [Click-to-inspect sequence](#click-to-inspect-sequence)
- [Session state machine](#session-state-machine)
- [Configuration composition](#configuration-composition)
- [Logging flow](#logging-flow)

---

## Class diagram

Domain, interfaces and implementations. `Environment` is the only object that
composes the three strategies into positional readings.

```mermaid
classDiagram
    direction LR

    class GameState {
        <<enumeration>>
        START
        PLAYING
        PAUSED
        END
    }

    class GameClock {
        +tick: int
        +paused: bool
        +accumulator: float
        +time_scale: float
        +set_time_scale(value)
    }

    class GameSession {
        +state: GameState
        +clock: GameClock
        +world: IWorld
        +environment: IEnvironment
        +end_reason: str
        +exit_requested: bool
    }

    class Calendar {
        +tick: int
        +day: int
        +day_fraction: float
        +clock: str
        +season: str
        +season_index: int
        +season_progress: float
        +day_of_season: int
        +year: int
        +advance(ticks)
        +reset()
    }

    class World {
        +width: float
        +height: float
        +cell_size: float
        +cols: int
        +rows: int
        +orientation: GradientOrientation
        +wrap_around: bool
        +barrier_strategy: IBarrierStrategy
        +cell_index(x, y) tuple
        +cell_center(col, row) tuple
        +add_barrier(barrier)
    }

    class Barrier {
        +id: int
        +kind: str
        +x: float
        +y: float
        +width: float
        +height: float
        +radius: float
        +color: tuple
    }

    class Environment {
        +calendar: ICalendar
        +season: str
        +phase: str
        +weather: str
        +light_level: float
        +palette: SeasonPalette
        +solar: SolarProfile
        +celestial: CelestialState
        +weather_at(x, y) str
        +light_at(x, y) float
        +humidity_at(x, y) float
        +pressure_at(x, y) float
        +temperature_at(x, y) float
        +advance_tick()
        +reset()
        -_temperature_gradient: Gradient
        -_humidity_gradient: Gradient
        -_pressure_gradient: Gradient
        -_light_gradient: Gradient
    }

    class Gradient {
        +orientation: GradientOrientation
        +start: float
        +end: float
        +factor(x, y, w, h) float
        +value(x, y, w, h) float
        +signed(x, y, w, h) float
    }

    class SolarProfile {
        +sun_intensity: float
        +daylight_fraction: float
    }

    class ClimateContext {
        +tick: int
        +season: str
        +solar: SolarProfile
        +base_temperature: float
        +humidity: float
        +pressure_hpa: float
        +weather_weights: dict
        +cols: int
        +rows: int
        +cell_size: float
        +adjusted_weather_weights() dict
        +climate_context() ClimateContext
    }

    class SeasonStrategy {
        +ticks_per_season: int
        +season_names: tuple
        +palette(calendar) SeasonPalette
        +solar_profile(calendar) SolarProfile
        +get_season_name(calendar) str
        +weather_weights(season) dict
    }

    class DayNightStrategy {
        +ticks_per_day: int
        +light_at(calendar, x, y, solar) float
        +phase(calendar, solar) str
        +celestial(calendar, solar) CelestialState
        +sky_palette() SkyPalette
    }

    class WeatherStrategy {
        +weather: str
        +weather_at(x, y) str
        +weather_at_cell(col, row) str
        +update(tick, climate)
        +reset()
        -_build(tick, climate)
        -_background_covers(col, row) bool
    }

    class BarrierStrategy {
        +color: tuple
        +max_span_cells: int
        +span_cells(barrier, world) tuple
        +validate(barrier, world)
        +create_barriers(world) list[Barrier]
    }

    class ArcadeView {
        +session: GameSession
        +set_input_handler(handler)
        +on_draw()
        +on_resize(w, h)
        +on_mouse_motion(x, y, dx, dy)
        +on_mouse_press(x, y, button, modifiers)
        +on_mouse_release(x, y, button, modifiers)
        -_layout: WorldLayout
        -_screen_to_world(sx, sy)
        -_world_to_screen(wx, wy)
        -_selected_cell: tuple
        -_hover_cell: tuple
        -_slider_rect: tuple
        -_text: _TextCache
    }

    class WorldLayout {
        +left: float
        +bottom: float
        +scale: float
        +cell_size: float
        +cols: int
        +rows: int
        +screen_to_world(sx, sy)
        +world_to_screen(wx, wy)
        +cell_index(x, y) tuple
        +cell_center(col, row) tuple
        +cell_screen_rect(col, row) tuple
    }

    class KeyboardInput {
        +handle_keypress(key)
        +set_time_scale(value)
    }

    class Container {
        +config: SimulationConfig
        +barrier_strategy: BarrierStrategy
        +world: World
        +calendar: Calendar
        +environment: Environment
        +session: GameSession
    }

    class ICalendar {
        <<interface>>
    }
    class ISeasonStrategy {
        <<interface>>
    }
    class IDayNightStrategy {
        <<interface>>
    }
    class IWeatherStrategy {
        <<interface>>
    }
    class IBarrierStrategy {
        <<interface>>
    }
    class IEnvironment {
        <<interface>>
    }
    class IWorld {
        <<interface>>
    }

    GameSession *-- GameClock
    GameSession --> IWorld
    GameSession --> IEnvironment

    Calendar ..|> ICalendar
    World ..|> IWorld

    SeasonStrategy ..|> ISeasonStrategy
    DayNightStrategy ..|> IDayNightStrategy
    WeatherStrategy ..|> IWeatherStrategy
    BarrierStrategy ..|> IBarrierStrategy
    Environment ..|> IEnvironment

    Environment --> ICalendar
    Environment --> ISeasonStrategy
    Environment --> IDayNightStrategy
    Environment --> IWeatherStrategy
    Environment --> IWorld
    Environment *-- Gradient

    WeatherStrategy --> IWorld

    BarrierStrategy --> IWorld
    Container --> BarrierStrategy
    Container --> World
    Container --> Calendar
    Container --> Environment
    Container --> GameSession

    ArcadeView --> GameSession
    KeyboardInput --> GameSession
    ArcadeView --> WorldLayout
```

---

## Wiring sequence

`main()` → `Container` → `GameSession`. Build order matters: the world provides
the cell grid used by weather, and the calendar needs the configured season
names.

```mermaid
sequenceDiagram
    autonumber
    participant M as main()
    participant C as Container
    participant W as World
    participant Cal as Calendar
    participant Env as Environment
    participant BS as BarrierStrategy
    participant Sess as GameSession
    participant Log as bean.* loggers

    M->>Log: configure_logging(config)
    Note over Log: BEAN_LOG_LEVEL > config.logging.level > INFO
    M->>Log: event=app.start
    M->>C: Container(config)

    C->>W: World(width, height, cell_size, orientation, barrier_strategy)
    C->>Cal: Calendar(ticks_per_day, ticks_per_season, names)
    C->>Env: build strategies (season, daynight, weather)
    Note over C,Env: strategy name None = static mode
    C->>Env: Environment(calendar, world, strategies, configs)
    Env->>Env: build one Gradient per reading
    Env->>Env: read first weather / day / season snapshot
    C->>BS: BarrierStrategy(config.barriers)
    BS->>W: create_barriers(world) -> list[Barrier]
    W->>W: add_barrier (validated by strategy)

    C->>Sess: GameSession(START, world, environment)
    C->>Log: container.built world, cells, seasons, strategies

    M->>Log: event=app.window_created (windowed only)
```

---

## Simulation tick sequence

Fixed-step, pause-aware. `advance_clock` is the only place wall-clock time is
turned into ticks, and the environment advances once per tick.

```mermaid
sequenceDiagram
    autonumber
    participant A as arcade on_update
    participant S as GameSession
    participant GC as GameClock
    participant Env as Environment
    participant Cal as Calendar
    participant W as WeatherStrategy
    participant Log as bean.* loggers

    A->>S: read state
    A->>GC: advance_clock(clock, real_dt, 1/tick_rate)
    GC-->>A: ticks_executed
    Note over GC: paused=True => 0 ticks, accumulator kept

    loop ticks_executed
        A->>Env: advance_tick()
        Env->>Cal: advance()
        Env->>Env: solar = season_strategy.solar_profile(calendar)
        Env->>W: update(calendar.tick, climate_context())
        W->>W: rebuild field when tick // change_interval changed

        opt day boundary
            Env->>Log: event=environment.day_changed
        end
        opt season boundary
            Env->>Log: event=environment.season_changed
        end
        opt aggregate weather changed
            Env->>Log: event=environment.weather_changed
        end
        opt readings enabled and DEBUG and interval elapsed
            Env->>Log: event=environment.reading ...
        end
    end

    alt session.exit_requested
        A->>Log: event=app.window_closing
        A->>A: view.close(), arcade.exit()
    end
```

---

## Reading composition

Each positional reading is a baseline from the season palette, plus weather
offsets, plus a positional gradient, plus a small microclimate term.

```mermaid
flowchart TD
    subgraph Inputs
        CAL[Calendar<br/>tick, season, day_fraction]
        SEASON[SeasonStrategy<br/>palette: base temp, swing,<br/>humidity, pressure, sun]
        SOLAR[SeasonStrategy<br/>solar_profile:<br/>sun_intensity, daylight_fraction]
        DAY[DayNightStrategy<br/>sun arc, local shading]
        WX[WeatherStrategy<br/>weather_at x y]
        GRAD[GradientConfig x4<br/>orientation, start, end]
        ENVC[EnvironmentConfig<br/>microclimate]
    end

    subgraph light
        L1[sun_arc × local_shading × sun_intensity]
        L2[× light_gradient]
        L3[× weather light factor]
        L4[clamp 0..1]
    end

    subgraph temperature
        T1[base + swing × 2·light − 1]
        T2[+ weather temperature offset]
        T3[+ temperature_gradient]
        T4[+ microclimate sin/cos]
    end

    subgraph humidity
        H1[season humidity]
        H2[+ weather humidity offset]
        H3[+ humidity_gradient]
        H4[+ microclimate noise]
    end

    subgraph pressure
        P1[season pressure hPa]
        P2[+ weather pressure offset]
        P3[+ pressure_gradient]
        P4[+ microclimate noise]
    end

    CAL --> L1
    DAY --> L1
    SOLAR --> L1
    SEASON --> T1
    CAL --> T1
    GRAD --> L2
    GRAD --> T3
    GRAD --> H3
    GRAD --> P3
    WX --> L3
    WX --> T2
    WX --> H2
    WX --> P2
    SEASON --> H1
    SEASON --> P1
    ENVC --> T4
    ENVC --> H4
    ENVC --> P4

    L1 --> L2 --> L3 --> L4
    L4 --> T1
    T1 --> T2 --> T3 --> T4
    H1 --> H2 --> H3 --> H4
    P1 --> P2 --> P3 --> P4
```

`GradientConfig.orientation` empty means "inherit `WorldConfig.orientation`".
Supported orientations: `north_south`, `south_north`, `west_east`, `east_west`,
`centre_out`, `out_centre`, `diagonal_up`, `diagonal_down`.

---

## Render / input loop

The view is read-only with respect to domain state. It samples the session and
never calls `advance_tick`.

```mermaid
flowchart LR
    subgraph Domain
        S[GameSession]
        E[Environment]
    end

    subgraph View
        V[ArcadeView.on_draw]
        L[_ensure_layout<br/>viewport size]
        WL[WorldLayout<br/>world ↔ screen + cells]
        W[_draw_world<br/>cols × rows × cell_size]
        BAR[_draw_barriers<br/>strategy colour]
        G[_draw_grid<br/>one line per cell boundary]
        SEL[_draw_selection<br/>integer cell index]
        SB[_draw_sidebar<br/>Time, Day, Season,<br/>Environment, Inspector,<br/>Weather field, Controls<br/>speed slider]
        TX[_TextCache<br/>arcade.Text objects]
    end

    subgraph Input
        K[KeyboardInput<br/>set_time_scale]
        MOUSE[on_mouse_press /<br/>on_mouse_motion /<br/>slider drag]
    end

    S --> V
    E --> V
    V --> L --> WL --> W --> BAR --> G --> SEL
    V --> SB
    W --> TX
    SB --> TX
    MOUSE -->|screen → world → cell_index| SEL
    MOUSE -->|slider → set_time_scale| K
    K -->|time_scale| S
    MOUSE -->|ui.cell_inspected| E
    K -->|state transitions| S
```

---

## Click-to-inspect sequence

Selection is stored as an integer `(col, row)`. The orange marker and the
readings both derive from it, so they cannot disagree.

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant V as ArcadeView
    participant W as World
    participant Env as Environment
    participant Log as bean.ui

    U->>V: mouse press (window x, y)
    V->>V: _mouse_to_screen(x, y)
    Note over V: scale by viewport / window size (HiDPI)
    V->>V: _screen_to_world(sx, sy)
    alt outside the world rectangle
        V->>V: _selected_cell = None
    else inside
        V->>W: cell_index(wx, wy)
        W-->>V: (col, row)
        V->>V: _selected_cell = (col, row)
        V->>W: cell_center(col, row)
        W-->>V: (cx, cy)
        V->>Env: weather_at, temperature_at,<br/>humidity_at, pressure_at, light_at
        Env-->>V: readings
        V->>Log: event=ui.cell_inspected cell=(c,r) ...
        V->>V: draw orange outline + crosshair at cell centre
        V->>V: sidebar Inspector reads the same cell
    end
```

---

## Session state machine

`KeyboardInput` is the only writer of `GameSession.state`.

```mermaid
stateDiagram-v2
    [*] --> START

    START --> PLAYING: SPACE
    START --> PAUSED: P
    START --> END: Esc

    PLAYING --> PAUSED: P
    PLAYING --> END: Q / Esc

    PAUSED --> PLAYING: P
    PAUSED --> END: Q / Esc

    END --> START: SPACE (restart)
    END --> [*]: Esc / Q

    note right of PAUSED
        clock.paused = True
        simulation ticks do not advance
    end note

    note left of END
        end_reason set
        exit_requested = True on quit
    end note
```

---

## Configuration composition

One module, no YAML. `DEFAULT_CONFIG` is the single object `main()` reads.

```mermaid
classDiagram
    direction TB

    class SimulationConfig {
        +tick_rate: float
        +debug: bool
        +world: WorldConfig
        +time: TimeConfig
        +barriers: BarrierConfig
        +seasons: list~SeasonConfig~
        +daynight: DayNightConfig
        +weather: WeatherConfig
        +environment: EnvironmentConfig
        +logging: LoggingConfig
    }

    class WorldConfig {
        +width: float
        +height: float
        +cell_size: float
        +orientation: GradientOrientation
        +wrap_around: bool
    }

    class BarrierConfig {
        +color: Color
        +max_span_cells: int
        +min_span_cells: int
        +count: int
        +seed: int
        +margin_cells: int
    }

    class TimeConfig {
        +ticks_per_day: int
        +ticks_per_season: int
        +start_tick: int
        +initial_time_scale: float
        +time_scale_min: float
        +time_scale_max: float
    }

    class SeasonConfig {
        +name: str
        +ground_color: tuple
        +ground_gradient: tuple
        +detail_colors: tuple
        +base_temperature: float
        +temperature_swing: float
        +humidity: float
        +pressure_hpa: float
        +sun_intensity: float
        +daylight_fraction: float
        +ground_meaning: str
        +weather_weights: dict
    }

    class DayNightConfig {
        +sun_speed: float
        +moon_speed: float
        +moon_phase_offset: float
        +local_shading: float
        +shading_scale_x: float
        +shading_scale_y: float
        +night_threshold: float
        +twilight_threshold: float
        +sun_arc_start: float
        +sun_arc_end: float
        +night_sky: Color
        +day_sky: Color
        +twilight_sky: Color
        +overcast_sky: Color
        +sun_color: Color
        +moon_color: Color
        +star_color: Color
    }

    class WeatherConfig {
        +change_interval: int
        +seed: int
        +front_count: int
        +background_coverage: float
        +front_radius_min_cells: int
        +front_radius_max_cells: int
        +front_drift_cells: float
        +background_patch_scale: float
        +temperature_offsets: dict
        +humidity_offsets: dict
        +pressure_offsets: dict
        +light_factors: dict
    }

    class EnvironmentConfig {
        +season_strategy: str
        +daynight_strategy: str
        +weather_strategy: str
        +temperature_gradient: GradientConfig
        +humidity_gradient: GradientConfig
        +pressure_gradient: GradientConfig
        +light_gradient: GradientConfig
        +microclimate: float
    }

    class GradientConfig {
        +start: float
        +end: float
        +orientation: GradientOrientation
    }

    class LoggingConfig {
        +level: str
        +format: str
        +date_format: str
        +business: bool
        +readings: bool
        +readings_interval: int
    }

    SimulationConfig *-- WorldConfig
    SimulationConfig *-- TimeConfig
    SimulationConfig *-- BarrierConfig
    SimulationConfig *-- "1..*" SeasonConfig
    SimulationConfig *-- DayNightConfig
    SimulationConfig *-- WeatherConfig
    SimulationConfig *-- EnvironmentConfig
    SimulationConfig *-- LoggingConfig
    EnvironmentConfig *-- GradientConfig
```

---

## Logging flow

Level resolution and the two log streams.

```mermaid
flowchart TD
    START([process start]) --> ENV{BEAN_LOG_LEVEL set?}
    ENV -->|yes| LEVEL[use it]
    ENV -->|no| CFG[config.logging.level]
    CFG -->|empty| INFO[INFO]
    CFG -->|value| LEVEL
    LEVEL --> SETUP[configure_logging<br/>bean.* namespace]
    SETUP --> OPS[operational stream<br/>app.*, container.*, weather.*, season.*]
    SETUP --> BIZ{business enabled?}
    BIZ -->|yes| EVT[business stream<br/>event=name key=value]
    BIZ -->|no| SILENT[no business events]
    EVT --> DBG{level == DEBUG<br/>and readings enabled?}
    DBG -->|yes| SAMPLE[environment.reading<br/>weather.front<br/>season.palette]
    DBG -->|no| DONE([run])
    SAMPLE --> DONE
    SILENT --> DONE
```

---

Back to [`README.md`](./README.md) · Original brief: [`spec.md`](./spec.md)
