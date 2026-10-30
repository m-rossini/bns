"""Default configuration for the simulation."""

from sim.config import (
    BarrierConfig,
    EnvironmentConfig,
    SimulationConfig,
    WorldConfig,
)

DEFAULT_CONFIG = SimulationConfig(
    world=WorldConfig(
        width=1200.0,
        height=800.0,
        orientation="north_south",
        wrap_around=False,
        barriers=[
            BarrierConfig(id=1, kind="rect", x=600.0, y=400.0, width=200.0, height=100.0),
            BarrierConfig(id=2, kind="circle", x=300.0, y=600.0, radius=60.0),
        ],
    ),
    environment=EnvironmentConfig(
        weather_strategy="WeatherStrategy",
        season_strategy="SeasonStrategy",
        daynight_strategy="DayNightStrategy",
    ),
    debug=False,
    tick_rate=30.0,
)
