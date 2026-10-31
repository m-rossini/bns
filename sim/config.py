"""Pure-Python configuration for the bean simulation.

No YAML/JSON. All tunable values live here as dataclasses.

Coordinate contract
-------------------
* The world is measured in **world units** (`WorldConfig.width/height`).
* It is divided into square **cells** of `WorldConfig.cell_size` world units:
  `cols = width / cell_size`, `rows = height / cell_size`.
* Weather, light and the environmental readings are sampled per cell.
* The view maps world units to screen pixels with a single uniform scale; it
  never assumes a pixel size for a cell.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

Color = Tuple[int, int, int]


@dataclass
class WorldConfig:
    width: float = 1200.0
    height: float = 800.0
    cell_size: float = 50.0
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
    """Tick -> date conversion. The calendar is the only time authority."""

    ticks_per_day: int = 1200          # 40 s per day at 30 ticks/s
    ticks_per_season: int = 4800       # 4 days per season
    start_tick: int = 0


@dataclass
class SeasonConfig:
    """One season definition. Add or remove these to change season count."""

    name: str = "Spring"
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
    night_sky: Color = (10, 14, 32)
    day_sky: Color = (122, 182, 228)
    twilight_sky: Color = (232, 138, 84)
    overcast_sky: Color = (92, 98, 110)
    sun_color: Color = (255, 228, 130)
    moon_color: Color = (222, 228, 245)
    star_color: Color = (235, 240, 255)


@dataclass
class WeatherConfig:
    """Per-cell weather field."""

    change_interval: int = 600         # ticks between weather systems
    seed: int = 1337
    front_count: int = 3               # number of moving weather systems
    background_coverage: float = 0.6   # fraction of cells under the background condition
    conditions: Tuple[str, ...] = ("clear", "cloudy", "rain", "storm", "snow")


@dataclass
class EnvironmentConfig:
    """Strategy class names, resolved by the DI container (`None` = static)."""

    weather_strategy: Optional[str] = None
    season_strategy: Optional[str] = None
    daynight_strategy: Optional[str] = None


@dataclass
class SimulationConfig:
    world: WorldConfig = field(default_factory=WorldConfig)
    time: TimeConfig = field(default_factory=TimeConfig)
    seasons: List[SeasonConfig] = field(default_factory=list)
    daynight: DayNightConfig = field(default_factory=DayNightConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    debug: bool = False
    tick_rate: float = 30.0  # simulation ticks per second


"""Default configuration for the simulation.

Season count, colours, temperatures and weather weights live here: change this
list to run a single permanently cold season, eight seasons, or anything else.
"""

DEFAULT_CONFIG = SimulationConfig(
    world=WorldConfig(
        width=1200.0,
        height=800.0,
        cell_size=50.0,  # 24 x 16 cells
        orientation="north_south",
        wrap_around=False,
    ),
    time=TimeConfig(
        ticks_per_day=1200,     # 40 s per day at 30 ticks/s
        ticks_per_season=4800,  # 4 days per season
    ),
    seasons=[
        SeasonConfig(
            name="Spring",
            ground_color=(96, 170, 88),
            detail_colors=[(250, 246, 180), (248, 186, 214), (232, 248, 236)],
            base_temperature=14.0,
            temperature_swing=7.0,
            humidity=0.55,
            pressure_hpa=1012.0,
            weather_weights={
                "clear": 30, "cloudy": 30, "rain": 30, "storm": 10, "snow": 0,
            },
        ),
        SeasonConfig(
            name="Summer",
            ground_color=(68, 146, 72),
            detail_colors=[(52, 122, 58), (92, 168, 84), (38, 110, 54)],
            base_temperature=25.0,
            temperature_swing=6.0,
            humidity=0.40,
            pressure_hpa=1015.0,
            weather_weights={
                "clear": 50, "cloudy": 25, "rain": 17, "storm": 8, "snow": 0,
            },
        ),
        SeasonConfig(
            name="Autumn",
            ground_color=(178, 128, 62),
            detail_colors=[(214, 124, 52), (166, 92, 42), (206, 168, 70)],
            base_temperature=13.0,
            temperature_swing=7.0,
            humidity=0.60,
            pressure_hpa=1010.0,
            weather_weights={
                "clear": 30, "cloudy": 35, "rain": 25, "storm": 10, "snow": 0,
            },
        ),
        SeasonConfig(
            name="Winter",
            ground_color=(222, 230, 236),
            detail_colors=[(246, 250, 255), (206, 222, 238), (232, 240, 248)],
            base_temperature=3.0,
            temperature_swing=5.0,
            humidity=0.70,
            pressure_hpa=1008.0,
            weather_weights={
                "clear": 25, "cloudy": 35, "rain": 0, "storm": 5, "snow": 35,
            },
        ),
    ],
    daynight=DayNightConfig(
        sun_speed=1.0,
        moon_speed=1.0,
        moon_phase_offset=0.25,
    ),
    weather=WeatherConfig(
        change_interval=600,
        seed=1337,
        front_count=3,
    ),
    environment=EnvironmentConfig(
        weather_strategy="WeatherStrategy",
        season_strategy="SeasonStrategy",
        daynight_strategy="DayNightStrategy",
    ),
    debug=False,
    tick_rate=30.0,
)
