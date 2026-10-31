"""Season strategy.

Seasons are configuration data (`SeasonConfig`): a name, a ground colour, its
detail speckles, a temperature baseline and swing, humidity, pressure and the
weather weights used by the weather strategy.

Changing the number of seasons needs no code change: list one, four or eight
entries in `SimulationConfig.seasons`.

The ground colour is a gradient over the season, derived from the configured
base colour so every season is a physical colour, not a hardcoded one:

* first half:   base darkened by 12% -> base
* second half:  base -> blend towards the next season's base

That produces a smooth seasonal change without touching the view.
"""

from typing import Dict, List, Sequence, Tuple

from sim.config import SeasonConfig
from sim.domain.visuals import SeasonPalette
from sim.interfaces.environment import ICalendar, ISeasonStrategy

Color = Tuple[int, int, int]

_FALLBACK = SeasonConfig(
    name="Season",
    ground_color=(120, 150, 120),
    detail_colors=[(140, 170, 140)],
    base_temperature=14.0,
    temperature_swing=6.0,
    humidity=0.5,
    pressure_hpa=1013.0,
    weather_weights={"clear": 40, "cloudy": 30, "rain": 20, "storm": 5, "snow": 5},
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def mix(a: Color, b: Color, t: float) -> Color:
    t = _clamp(t, 0.0, 1.0)
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def shade(color: Color, factor: float) -> Color:
    return tuple(max(0, min(255, int(round(c * factor)))) for c in color[:3])


def seasonal_gradient(base: Color, next_base: Color, progress: float) -> Color:
    """Ground colour for a moment inside a season."""
    progress = _clamp(progress, 0.0, 1.0)
    if progress <= 0.5:
        return mix(shade(base, 0.88), base, progress / 0.5)
    return mix(base, mix(base, next_base, 0.28), (progress - 0.5) / 0.5)


class SeasonStrategy(ISeasonStrategy):
    def __init__(self, seasons: Sequence[SeasonConfig], ticks_per_season: int):
        if not seasons:
            raise ValueError("at least one season is required")
        if ticks_per_season <= 0:
            raise ValueError("ticks_per_season must be positive")

        self._seasons: List[SeasonConfig] = list(seasons)
        self._by_name: Dict[str, SeasonConfig] = {s.name: s for s in self._seasons}
        self._ticks_per_season = ticks_per_season

    @property
    def ticks_per_season(self) -> int:
        return self._ticks_per_season

    @property
    def season_names(self) -> Tuple[str, ...]:
        return tuple(s.name for s in self._seasons)

    def _definition(self, season: str) -> SeasonConfig:
        return self._by_name.get(season, _FALLBACK)

    def _next_definition(self, season: str) -> SeasonConfig:
        for index, definition in enumerate(self._seasons):
            if definition.name == season:
                return self._seasons[(index + 1) % len(self._seasons)]
        return _FALLBACK

    def get_season_name(self, calendar: ICalendar) -> str:
        """Return the current season name from the strategy perspective."""
        return calendar.season

    def weather_weights(self, season: str) -> Dict[str, float]:
        return dict(self._definition(season).weather_weights)

    def palette(self, calendar: ICalendar) -> SeasonPalette:
        season = calendar.season
        definition = self._definition(season)
        next_definition = self._next_definition(season)

        ground = seasonal_gradient(
            definition.ground_color,
            next_definition.ground_color,
            calendar.season_progress,
        )
        details = tuple(definition.detail_colors) or (shade(ground, 0.8),)

        return SeasonPalette(
            name=definition.name,
            ground=ground,
            details=details,
            base_temperature=definition.base_temperature,
            temperature_swing=definition.temperature_swing,
            humidity=definition.humidity,
            pressure_hpa=definition.pressure_hpa,
        )
