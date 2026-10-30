"""Day/night cycle strategy.

One full day is ``ticks_per_day`` simulation ticks. Light follows a cosine so
midnight is dark, noon is bright, and dawn/dusk pass through twilight.
"""

import math

from sim.interfaces.environment import IDayNightStrategy


class DayNightStrategy(IDayNightStrategy):
    def __init__(self, ticks_per_day: int = 1200):
        if ticks_per_day <= 0:
            raise ValueError("ticks_per_day must be positive")
        self._ticks_per_day = ticks_per_day

    @property
    def ticks_per_day(self) -> int:
        return self._ticks_per_day

    def _progress(self, tick: int) -> float:
        """Fraction of the current day, 0.0 = midnight, 0.5 = noon."""
        return (tick % self._ticks_per_day) / self._ticks_per_day

    def get_light_level(self, tick: int) -> float:
        # 0.0 at midnight, 1.0 at noon.
        return 0.5 - 0.5 * math.cos(2.0 * math.pi * self._progress(tick))

    def get_phase(self, tick: int) -> str:
        light = self.get_light_level(tick)
        progress = self._progress(tick)
        if light < 0.12:
            return "night"
        if light < 0.45:
            return "dawn" if progress < 0.5 else "dusk"
        return "day"
