"""Weather strategy.

Picks a new condition every ``change_interval`` ticks. The choice is
deterministic for a given seed and tick, so runs are reproducible.
Snow is only possible in winter and rain is suppressed in winter.
"""

import random

from sim.interfaces.environment import IEnvironment, IWeatherStrategy


class WeatherStrategy(IWeatherStrategy):
    CONDITIONS = ("clear", "cloudy", "rain", "storm", "snow")

    # Relative weights by season. Snow only in winter, rain only outside it.
    _WEIGHTS = {
        "spring": {"clear": 30, "cloudy": 30, "rain": 30, "storm": 10, "snow": 0},
        "summer": {"clear": 50, "cloudy": 25, "rain": 17, "storm": 8, "snow": 0},
        "autumn": {"clear": 30, "cloudy": 35, "rain": 25, "storm": 10, "snow": 0},
        "winter": {"clear": 25, "cloudy": 35, "rain": 0, "storm": 5, "snow": 35},
    }

    def __init__(self, change_interval: int = 600, seed: int = 1337):
        if change_interval <= 0:
            raise ValueError("change_interval must be positive")
        self._change_interval = change_interval
        self._seed = seed
        self._weather = "clear"

    @property
    def weather(self) -> str:
        return self._weather

    def reset(self) -> None:
        self._weather = "clear"

    def update(self, tick: int, environment: IEnvironment) -> None:
        if tick % self._change_interval != 0:
            return

        rng = random.Random((self._seed, tick // self._change_interval))
        weights = self._WEIGHTS.get(environment.season, self._WEIGHTS["spring"])
        conditions = [c for c in self.CONDITIONS if weights[c] > 0]
        choices = [weights[c] for c in conditions]
        self._weather = rng.choices(conditions, weights=choices, k=1)[0]
