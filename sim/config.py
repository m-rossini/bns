"""Pure-Python configuration for the bean simulation.

No YAML/JSON. All tunable values live here as dataclasses. This module is the
single source of truth for world size, time, seasons, day/night, weather,
environment gradients and logging. Nothing else hardcodes a tunable constant.

Coordinate contract
-------------------
* The world is measured in **world units** (`WorldConfig.width/height`).
* It is divided into square **cells** of `WorldConfig.cell_size` world units:
  `cols = width / cell_size`, `rows = height / cell_size`.
* Weather, light and the environmental readings are sampled per cell.
* The view maps world units to screen pixels with a single uniform scale; it
  never assumes a pixel size for a cell.

Gradients
---------
Numeric readings use `GradientConfig(start, end, orientation)`: the value is
interpolated from ``start`` at one edge to ``end`` at the opposite edge.
Colour gradients use a plain ``(start_colour, end_colour)`` tuple, e.g.
``ground_gradient=((80, 150, 80), (140, 200, 110))``.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

Color = Tuple[int, int, int]

#: Valid values for `GradientConfig.orientation` and `WorldConfig.orientation`.
GRADIENT_ORIENTATIONS: Tuple[str, ...] = (
    "north_south",
    "south_north",
    "west_east",
    "east_west",
    "centre_out",
    "out_centre",
    "diagonal_up",
    "diagonal_down",
)


@dataclass
class WorldConfig:
    width: float = 1200.0
    height: float = 800.0
    cell_size: float = 10.0
    #: Direction used by climate gradients. Empty string = north_south.
    orientation: str = "north_south"
    wrap_around: bool = False

    @property
    def cols(self) -> int:
        return max(1, int(round(self.width / self.cell_size)))

    @property
    def rows(self) -> int:
        return max(1, int(round(self.height / self.cell_size)))


@dataclass
class TimeConfig:
    """Tick -> date conversion. The calendar is the only time authority.

    ``time_scale`` is the playback/perception multiplier applied by the
    ticker: it slows or speeds how fast simulated time *appears* to pass
    without touching the fixed-step tick accumulation or ``tick_rate``.
    """

    ticks_per_day: int = 1200          # 40 s per day at 30 ticks/s
    ticks_per_season: int = 4800       # 4 days per season
    start_tick: int = 0
    initial_time_scale: float = 1.0    # perceived speed at startup (1.0 = real time)
    time_scale_min: float = 0.1        # slowest the slider can go
    time_scale_max: float = 4.0        # fastest the slider can go


@dataclass(frozen=True)
class GradientConfig:
    """Linear ``start -> end`` gradient across the world.

    ``orientation`` is one of `GRADIENT_ORIENTATIONS`; an empty string means
    "inherit `WorldConfig.orientation`". The value at a position is
    ``start + (end - start) * factor`` where ``factor`` runs 0..1 along the
    chosen direction.
    """

    start: float = 0.0
    end: float = 1.0
    orientation: str = ""


@dataclass
class SeasonConfig:
    """One season definition. Add or remove these to change season count.

    ``ground_gradient`` is an explicit ``(start, end)`` colour pair evaluated
    over the season's progress. Leave it ``None`` to derive the ground colour
    from ``ground_color`` and the next season's colour instead.
    """

    name: str = "Spring"
    ground_color: Color = (96, 170, 88)
    ground_gradient: Optional[Tuple[Color, Color]] = None
    detail_colors: List[Color] = field(default_factory=list)
    base_temperature: float = 14.0     # deg C, seasonal mean
    temperature_swing: float = 7.0     # deg C, day/night amplitude
    humidity: float = 0.55             # 0..1 seasonal baseline
    pressure_hpa: float = 1013.0       # seasonal baseline
    #: Human-readable meaning of this season's ground colour, shown in the
    #  view legend (e.g. "growing season" vs "dry / dormant"). Owned by the
    #  season strategy, not random.
    ground_meaning: str = "growing season"
    #: Peak sun brightness the season allows (>1 summer, <1 winter).
    sun_intensity: float = 1.0
    #: Share of the day the sun is above the horizon (0.5 = 12 h).
    daylight_fraction: float = 0.5
    weather_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class DayNightConfig:
    """Sun/moon cycle and local light shaping.

    The *amount* of sun (peak intensity and day length) belongs to the season
    strategy; this config only shapes how that solar profile is rendered.
    ``local_shading`` is the amplitude of the smooth terrain/cover shading.
    """

    sun_speed: float = 1.0             # multiplier on the sun arc
    moon_speed: float = 1.0            # multiplier on the moon arc
    moon_phase_offset: float = 0.25    # 0..1, shifts the moon's phase

    local_shading: float = 0.10        # 0..1 amplitude of positional shading
    shading_scale_x: float = 190.0     # world units between shading lobes
    shading_scale_y: float = 150.0

    night_threshold: float = 0.12      # below this altitude it is night
    twilight_threshold: float = 0.45   # below this it is dawn/dusk

    night_sky: Color = (10, 14, 32)
    day_sky: Color = (122, 182, 228)
    twilight_sky: Color = (232, 138, 84)
    overcast_sky: Color = (92, 98, 110)
    sun_color: Color = (255, 228, 130)
    moon_color: Color = (222, 228, 245)
    star_color: Color = (235, 240, 255)


def _default_temperature_offsets() -> Dict[str, float]:
    return {"clear": 2.0, "cloudy": 0.0, "rain": -2.0, "storm": -4.0, "snow": -5.0}


def _default_humidity_offsets() -> Dict[str, float]:
    return {"clear": -0.10, "cloudy": 0.02, "rain": 0.20, "storm": 0.25, "snow": 0.08}


def _default_pressure_offsets() -> Dict[str, float]:
    return {"clear": 4.0, "cloudy": -3.0, "rain": -8.0, "storm": -18.0, "snow": -5.0}


def _default_light_factors() -> Dict[str, float]:
    return {"clear": 1.0, "cloudy": 0.82, "rain": 0.68, "storm": 0.5, "snow": 0.85}


@dataclass
class WeatherConfig:
    """Per-cell weather field.

    ``front_radius_min_cells`` / ``front_radius_max_cells`` are measured in
    grid cells; ``0`` means "derive from the grid size". Each front is a disc
    of one condition and moves between field rebuilds, so neighbouring cells
    differ instead of showing one global condition.
    """

    change_interval: int = 600         # ticks between weather systems
    seed: int = 1337
    front_count: int = 3               # number of moving weather systems
    background_coverage: float = 0.6   # fraction of cells under the background condition
    front_radius_min_cells: int = 0    # 0 = auto
    front_radius_max_cells: int = 0    # 0 = auto
    front_drift_cells: float = 0.0     # optional movement per rebuild
    background_patch_scale: float = 1.0  # >1 = smaller, more frequent patches
    conditions: Tuple[str, ...] = ("clear", "cloudy", "rain", "storm", "snow")

    # Physical effect of each condition. These are what make neighbouring
    # cells read differently, together with the climate gradients.
    temperature_offsets: Dict[str, float] = field(default_factory=_default_temperature_offsets)
    humidity_offsets: Dict[str, float] = field(default_factory=_default_humidity_offsets)
    pressure_offsets: Dict[str, float] = field(default_factory=_default_pressure_offsets)
    light_factors: Dict[str, float] = field(default_factory=_default_light_factors)


@dataclass
class BarrierConfig:
    """Static obstacles and the rules that shape them.

    ``color`` is the fill used by every barrier; ``max_span_cells`` caps how
    many grid cells a barrier may cover in either direction (3 = at most
    3x3), which keeps obstacles small and cell-aligned. ``count`` barriers are
    generated deterministically from ``seed`` and distributed over the world.
    """

    color: Color = (255, 208, 64)      # yellow
    max_span_cells: int = 3            # <= 3 cells wide and <= 3 cells tall
    min_span_cells: int = 1
    count: int = 6
    seed: int = 4242
    margin_cells: int = 1              # keep barriers away from the border

    def __post_init__(self) -> None:
        if self.max_span_cells < 1:
            raise ValueError("BarrierConfig.max_span_cells must be >= 1")
        if self.min_span_cells < 1:
            raise ValueError("BarrierConfig.min_span_cells must be >= 1")
        if self.min_span_cells > self.max_span_cells:
            raise ValueError(
                "BarrierConfig.min_span_cells cannot exceed max_span_cells"
            )
        if self.count < 0:
            raise ValueError("BarrierConfig.count cannot be negative")
        if self.margin_cells < 0:
            raise ValueError("BarrierConfig.margin_cells cannot be negative")


@dataclass
class EnvironmentConfig:
    """Strategy class names and positional climate gradients.

    ``None`` for a strategy means "static": the environment keeps running but
    that reading falls back to a documented constant.
    """

    weather_strategy: Optional[str] = None
    season_strategy: Optional[str] = None
    daynight_strategy: Optional[str] = None

    # Gradients are added to the season baseline. The orientation falls back
    # to `WorldConfig.orientation` when left empty.
    temperature_gradient: GradientConfig = field(
        default_factory=lambda: GradientConfig(-4.0, 4.0)
    )
    humidity_gradient: GradientConfig = field(
        default_factory=lambda: GradientConfig(-0.12, 0.12)
    )
    pressure_gradient: GradientConfig = field(
        default_factory=lambda: GradientConfig(-6.0, 6.0)
    )
    light_gradient: GradientConfig = field(
        default_factory=lambda: GradientConfig(0.88, 1.08)
    )
    #: Scales the fine-grained sin/cos microclimate noise (0 disables it).
    microclimate: float = 1.0


@dataclass
class LoggingConfig:
    """Runtime logging configuration.

    The environment variable ``BEAN_LOG_LEVEL`` overrides ``level``; the
    Makefile exposes it as ``LOG_LEVEL``. Levels: DEBUG, INFO, WARNING,
    ERROR, CRITICAL.
    """

    level: str = "INFO"
    format: str = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"
    date_format: str = "%H:%M:%S"
    business: bool = True       # emit gameplay/business events
    readings: bool = True       # emit per-cell reading samples at DEBUG
    readings_interval: int = 60  # ticks between DEBUG reading samples


@dataclass
class SimulationConfig:
    world: WorldConfig = field(default_factory=WorldConfig)
    time: TimeConfig = field(default_factory=TimeConfig)
    seasons: List[SeasonConfig] = field(default_factory=list)
    daynight: DayNightConfig = field(default_factory=DayNightConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    barriers: BarrierConfig = field(default_factory=BarrierConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    debug: bool = False
    tick_rate: float = 30.0  # simulation ticks per second


"""Default configuration for the simulation.

Season count, colours, gradients, temperatures and weather weights live here:
change this list to run a single permanently cold season, eight seasons, or
anything else. Every value below is a documented default; override a field to
change the simulation without touching code.
"""

DEFAULT_CONFIG = SimulationConfig(
    world=WorldConfig(
        width=1200.0,
        height=800.0,
        cell_size=10.0,  # 120 x 80 cells
        orientation="north_south",
        wrap_around=False,
    ),
    time=TimeConfig(
        ticks_per_day=1200,     # 40 s per day at 30 ticks/s
        ticks_per_season=4800,  # 4 days per season
        initial_time_scale=1.0,
        time_scale_min=0.1,
        time_scale_max=4.0,
    ),
    seasons=[
        SeasonConfig(
            name="Spring",
            ground_color=(96, 170, 88),
            ground_gradient=((82, 148, 78), (128, 196, 104)),
            detail_colors=[(250, 246, 180), (248, 186, 214), (232, 248, 236)],
            base_temperature=14.0,
            temperature_swing=7.0,
            humidity=0.55,
            pressure_hpa=1012.0,
            ground_meaning="growing season",
            sun_intensity=0.95,
            daylight_fraction=0.50,
            weather_weights={
                "clear": 30, "cloudy": 30, "rain": 30, "storm": 10, "snow": 0,
            },
        ),
        SeasonConfig(
            name="Summer",
            ground_color=(68, 146, 72),
            ground_gradient=((78, 164, 82), (52, 126, 60)),
            detail_colors=[(52, 122, 58), (92, 168, 84), (38, 110, 54)],
            base_temperature=25.0,
            temperature_swing=6.0,
            humidity=0.40,
            pressure_hpa=1015.0,
            ground_meaning="peak growing season",
            sun_intensity=1.15,
            daylight_fraction=0.60,
            weather_weights={
                "clear": 50, "cloudy": 25, "rain": 17, "storm": 8, "snow": 0,
            },
        ),
        SeasonConfig(
            name="Autumn",
            ground_color=(178, 128, 62),
            ground_gradient=((196, 156, 74), (148, 94, 44)),
            detail_colors=[(214, 124, 52), (166, 92, 42), (206, 168, 70)],
            base_temperature=13.0,
            temperature_swing=7.0,
            humidity=0.60,
            pressure_hpa=1010.0,
            ground_meaning="dry / dormant",
            sun_intensity=0.82,
            daylight_fraction=0.45,
            weather_weights={
                "clear": 30, "cloudy": 35, "rain": 25, "storm": 10, "snow": 0,
            },
        ),
        SeasonConfig(
            name="Winter",
            ground_color=(222, 230, 236),
            ground_gradient=((236, 242, 248), (198, 212, 226)),
            detail_colors=[(246, 250, 255), (206, 222, 238), (232, 240, 248)],
            base_temperature=3.0,
            temperature_swing=5.0,
            humidity=0.70,
            pressure_hpa=1008.0,
            ground_meaning="dormant / cold",
            sun_intensity=0.55,
            daylight_fraction=0.34,
            weather_weights={
                "clear": 25, "cloudy": 35, "rain": 0, "storm": 5, "snow": 35,
            },
        ),
    ],
    daynight=DayNightConfig(
        sun_speed=1.0,
        moon_speed=1.0,
        moon_phase_offset=0.25,
        local_shading=0.10,
        shading_scale_x=190.0,
        shading_scale_y=150.0,
    ),
    weather=WeatherConfig(
        change_interval=600,
        seed=1337,
        front_count=3,
        background_coverage=0.6,
        front_radius_min_cells=2,
        front_radius_max_cells=6,
    ),
    barriers=BarrierConfig(
        color=(255, 208, 64),      # yellow default
        max_span_cells=3,          # 3x3, 3x1, 1x2, ...
        min_span_cells=1,
        count=6,
        seed=4242,
        margin_cells=1,
    ),
    environment=EnvironmentConfig(
        weather_strategy="WeatherStrategy",
        season_strategy="SeasonStrategy",
        daynight_strategy="DayNightStrategy",
        temperature_gradient=GradientConfig(-4.0, 4.0),
        humidity_gradient=GradientConfig(-0.12, 0.12),
        pressure_gradient=GradientConfig(-6.0, 6.0),
        light_gradient=GradientConfig(0.88, 1.08),
        microclimate=1.0,
    ),
    logging=LoggingConfig(level="INFO"),
    debug=False,
    tick_rate=30.0,
)
