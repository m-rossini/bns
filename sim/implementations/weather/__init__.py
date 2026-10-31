"""Weather strategy: a per-cell weather field.

The field is the union of two layers:

* a **background** condition taken from the season's weights, applied to a
  patchy subset of cells (``background_coverage``) so it never fills the whole
  grid uniformly;
* a handful of moving **fronts**, each a disc of a different condition.

A new field is generated every ``change_interval`` ticks, deterministically
from the seed, so runs are reproducible while neighbouring cells share a
condition instead of being independently random.

The strategy receives a `ClimateContext` on every update: season, world
geometry, temperature, humidity, pressure and the season's solar profile. Those
inputs reshape the season's weights (`ClimateContext.adjusted_weather_weights`)
so, for example, rain falls as snow below freezing and storms need warmth and
moisture. Snow never appears in a season whose weights do not allow it.
"""

import math
import random
from typing import Dict, List, Optional

from sim.config import WeatherConfig
from sim.domain.climate import ClimateContext
from sim.interfaces.environment import IWeatherStrategy
from sim.interfaces.world import IWorld
from sim.observability import get_logger

logger = get_logger("weather")

_SEVERITY = {"clear": 0, "cloudy": 1, "rain": 2, "snow": 2, "storm": 3}


class _Front:
    __slots__ = ("col", "row", "radius", "kind")

    def __init__(self, col: float, row: float, radius: float, kind: str):
        self.col = col
        self.row = row
        self.radius = radius
        self.kind = kind

    def covers(self, col: int, row: int) -> bool:
        dx = col + 0.5 - self.col
        dy = row + 0.5 - self.row
        return math.hypot(dx, dy) <= self.radius


class WeatherStrategy(IWeatherStrategy):
    def __init__(self, config: WeatherConfig, world: IWorld):
        if config.change_interval <= 0:
            raise ValueError("change_interval must be positive")
        self._config = config
        self._cols = world.cols
        self._rows = world.rows
        self._cell_size = world.cell_size
        self._base = "clear"
        self._coverage = max(0.0, min(1.0, config.background_coverage))
        self._fronts: List[_Front] = []
        self._interval: Optional[int] = None

    # ------------------------------------------------------------------
    # Field generation
    # ------------------------------------------------------------------
    @staticmethod
    def _choose(rng: random.Random, weights: Dict[str, float]) -> str:
        options = [(k, w) for k, w in weights.items() if w > 0]
        if not options:
            return "clear"
        kinds = [k for k, _ in options]
        values = [w for _, w in options]
        return rng.choices(kinds, weights=values, k=1)[0]

    def _build(self, tick: int, climate: ClimateContext) -> None:
        interval = tick // self._config.change_interval
        season = climate.season
        weights = climate.adjusted_weather_weights()

        rng = random.Random((self._config.seed, interval, season))
        self._base = self._choose(rng, weights)

        min_cells = min(self._cols, self._rows)
        low = self._config.front_radius_min_cells or max(2, min_cells // 8)
        high = self._config.front_radius_max_cells or max(low + 1, min_cells // 3)
        if high <= low:
            high = low + 1

        drift = self._config.front_drift_cells * interval
        fronts: List[_Front] = []
        for _ in range(max(0, self._config.front_count)):
            col = (rng.uniform(0, self._cols) + drift) % max(1, self._cols)
            row = (rng.uniform(0, self._rows) + drift * 0.5) % max(1, self._rows)
            radius = rng.uniform(low, high)
            fronts.append(_Front(col, row, radius, self._choose(rng, weights)))

        self._fronts = fronts
        self._interval = interval

        logger.info(
            "weather.field_rebuilt interval=%s season=%s base=%s coverage=%.2f "
            "fronts=%s radius=%s..%s temp=%.1f humidity=%.2f pressure=%.0f "
            "sun=%.2f daylight=%.2f",
            interval,
            season,
            self._base,
            self._coverage,
            len(fronts),
            low,
            high,
            climate.mean_temperature,
            climate.humidity,
            climate.pressure_hpa,
            climate.sun_intensity,
            climate.daylight_fraction,
        )
        for index, front in enumerate(fronts):
            logger.debug(
                "weather.front index=%d kind=%s col=%.2f row=%.2f radius=%.2f",
                index,
                front.kind,
                front.col,
                front.row,
                front.radius,
            )

    def update(self, tick: int, climate: ClimateContext) -> None:
        interval = tick // self._config.change_interval
        if self._interval != interval or self._interval is None:
            self._build(tick, climate)

    # ------------------------------------------------------------------
    # Readings
    # ------------------------------------------------------------------
    @property
    def weather(self) -> str:
        return self._base

    def _background_covers(self, col: int, row: int) -> bool:
        """Patchy, deterministic mask so the background is never uniform."""
        interval = self._interval or 0
        phase = interval * 0.37
        scale = max(0.05, self._config.background_patch_scale)
        patch = 0.5 + 0.5 * math.sin(col * 0.71 * scale + phase) * math.cos(
            row * 0.93 * scale - phase
        )
        patch += 0.28 * math.sin((col + row) * 0.41 * scale + phase * 1.7)
        return patch / 1.28 < self._coverage

    def weather_at_cell(self, col: int, row: int) -> str:
        best = self._base if self._background_covers(col, row) else "clear"
        for front in self._fronts:
            if front.covers(col, row):
                if _SEVERITY.get(front.kind, 0) > _SEVERITY.get(best, 0):
                    best = front.kind
        return best

    def weather_at(self, x: float, y: float) -> str:
        col = int(x // self._cell_size)
        row = int(y // self._cell_size)
        col = max(0, min(self._cols - 1, col))
        row = max(0, min(self._rows - 1, row))
        return self.weather_at_cell(col, row)

    def reset(self) -> None:
        self._base = "clear"
        self._fronts = []
        self._interval = None
