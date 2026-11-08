"""Season strategy.

Seasons are configuration data (`SeasonConfig`): a name, a ground colour, its
detail speckles, a temperature baseline and swing, humidity, pressure, the
amount of sun the world receives and the weather weights used by the weather
strategy.

Changing the number of seasons needs no code change: list one, four or eight
entries in `SimulationConfig.seasons`.

The season also owns **how much sun** the world gets: `solar_profile()` blends
the current season's `sun_intensity` and `daylight_fraction` into the next one
over the final quarter of the season, so the hand-over is smooth and the
day/night strategy never has to know about seasons.

The ground colour is a gradient over the season, derived from the configured
base colour so every season is a physical colour, not a hardcoded one:

* first half:   base darkened by 12% -> base
* second half:  base -> blend towards the next season's base

That produces a smooth seasonal change without touching the view.
"""

import random
from dataclasses import replace
from typing import Dict, List, Optional, Sequence, Tuple

from sim.config import SeasonConfig
from sim.domain.visuals import SeasonPalette, SolarProfile
from sim.interfaces.environment import ICalendar, ISeasonStrategy
from sim.observability import get_logger

logger = get_logger("season")

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


def _smoothstep(value: float) -> float:
    value = _clamp(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def transition_weight(progress: float) -> float:
    """How far the solar profile has moved towards the next season.

    Stays at 0 for the first three quarters of the season, then eases to 1 so
    the season boundary is continuous.
    """
    return _smoothstep((_clamp(progress, 0.0, 1.0) - 0.75) / 0.25)


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


def gradient_color(start: Color, end: Color, progress: float) -> Color:
    """Explicit ``(start, end)`` colour gradient over a season."""
    return mix(start, end, _clamp(progress, 0.0, 1.0))


class SeasonStrategy(ISeasonStrategy):
    def __init__(
        self,
        seasons: Sequence[SeasonConfig],
        ticks_per_season: int,
        seed: Optional[int] = None,
    ):
        if not seasons:
            raise ValueError("at least one season is required")
        if ticks_per_season <= 0:
            raise ValueError("ticks_per_season must be positive")

        self._seasons: List[SeasonConfig] = list(seasons)
        self._by_name: Dict[str, SeasonConfig] = {s.name: s for s in self._seasons}
        self._ticks_per_season = ticks_per_season
        self._seed = (
            int(seed)
            if seed is not None
            else random.SystemRandom().randrange(1, 2**63)
        )
        self._variation_cache: Dict[Tuple[int, int], SeasonConfig] = {}

    @property
    def ticks_per_season(self) -> int:
        return self._ticks_per_season

    @property
    def season_names(self) -> Tuple[str, ...]:
        return tuple(s.name for s in self._seasons)

    def _index(self, season: str) -> Optional[int]:
        for index, definition in enumerate(self._seasons):
            if definition.name == season:
                return index
        return None

    def _definition(self, season: str) -> SeasonConfig:
        return self._by_name.get(season, _FALLBACK)

    def _varied(self, index: int, year: int) -> SeasonConfig:
        """Return the season definition for one concrete year.

        Year 1 is the configured baseline. Later years sample a bounded
        variation from a stable per-occurrence RNG, so the same year and seed
        always produce the same season and successive cycles do not repeat.
        """
        base = self._seasons[index]
        if year <= 1:
            return base

        key = (year, index)
        cached = self._variation_cache.get(key)
        if cached is not None:
            return cached

        rng = random.Random(f"{self._seed}:{year}:{index}")
        weights = {
            name: max(
                0.0,
                weight
                * (1.0 + rng.uniform(
                    -base.weather_weight_variation,
                    base.weather_weight_variation,
                )),
            )
            for name, weight in base.weather_weights.items()
        }
        varied = replace(
            base,
            base_temperature=(
                base.base_temperature
                + rng.uniform(-base.temperature_variation, base.temperature_variation)
            ),
            temperature_swing=max(
                0.0,
                base.temperature_swing
                + rng.uniform(
                    -base.temperature_swing_variation,
                    base.temperature_swing_variation,
                ),
            ),
            humidity=_clamp(
                base.humidity
                + rng.uniform(-base.humidity_variation, base.humidity_variation),
                0.0,
                1.0,
            ),
            pressure_hpa=(
                base.pressure_hpa
                + rng.uniform(-base.pressure_variation, base.pressure_variation)
            ),
            sun_intensity=max(
                0.0,
                base.sun_intensity
                + rng.uniform(
                    -base.sun_intensity_variation,
                    base.sun_intensity_variation,
                ),
            ),
            daylight_fraction=_clamp(
                base.daylight_fraction
                + rng.uniform(-base.daylight_variation, base.daylight_variation),
                0.05,
                0.95,
            ),
            weather_weights=weights,
        )
        self._variation_cache[key] = varied
        return varied

    def _current(self, calendar: ICalendar) -> SeasonConfig:
        index = self._index(calendar.season)
        if index is None:
            return _FALLBACK
        return self._varied(index, calendar.year)

    def _following(self, calendar: ICalendar) -> SeasonConfig:
        index = self._index(calendar.season)
        if index is None:
            return _FALLBACK
        next_index = (index + 1) % len(self._seasons)
        next_year = calendar.year + (1 if next_index == 0 else 0)
        return self._varied(next_index, next_year)

    def get_season_name(self, calendar: ICalendar) -> str:
        """Return the current season name from the strategy perspective."""
        return self._definition(calendar.season).name

    def weather_weights(self, season: str, year: int = 1) -> Dict[str, float]:
        index = self._index(season)
        if index is None:
            return dict(_FALLBACK.weather_weights)
        return dict(self._varied(index, year).weather_weights)

    def snapshot_state(self) -> dict:
        """Persist the resolved variation seed for exact resume."""
        return {"seed": self._seed}

    def restore_state(self, state: dict) -> None:
        seed = state.get("seed")
        if seed is not None:
            self._seed = int(seed)
        self._variation_cache.clear()

    def palette(self, calendar: ICalendar) -> SeasonPalette:
        definition = self._current(calendar)
        next_definition = self._following(calendar)
        progress = calendar.season_progress

        if definition.ground_gradient is not None:
            start, end = definition.ground_gradient
            ground = gradient_color(start, end, progress)
        else:
            ground = seasonal_gradient(
                definition.ground_color,
                next_definition.ground_color,
                progress,
            )
        details = tuple(definition.detail_colors) or (shade(ground, 0.8),)

        palette = SeasonPalette(
            name=definition.name,
            ground=ground,
            details=details,
            base_temperature=definition.base_temperature,
            temperature_swing=definition.temperature_swing,
            humidity=definition.humidity,
            pressure_hpa=definition.pressure_hpa,
            sun_intensity=definition.sun_intensity,
            daylight_fraction=definition.daylight_fraction,
            ground_meaning=definition.ground_meaning,
        )
        logger.debug(
            "season.palette season=%s progress=%.3f ground=%s sun=%.2f daylight=%.2f "
            "ground_meaning=%s",
            definition.name,
            progress,
            ground,
            definition.sun_intensity,
            definition.daylight_fraction,
            definition.ground_meaning,
        )
        return palette

    def solar_profile(self, calendar: ICalendar) -> SolarProfile:
        """Sun the world gets now, easing into the next season's profile."""
        current = self._current(calendar)
        following = self._following(calendar)
        weight = transition_weight(calendar.season_progress)

        intensity = current.sun_intensity + (
            following.sun_intensity - current.sun_intensity
        ) * weight
        daylight = current.daylight_fraction + (
            following.daylight_fraction - current.daylight_fraction
        ) * weight
        return SolarProfile(
            sun_intensity=max(0.0, intensity),
            daylight_fraction=_clamp(daylight, 0.05, 0.95),
        )
