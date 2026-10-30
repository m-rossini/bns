"""Season cycle strategy.

Seasons rotate spring -> summer -> autumn -> winter, one season every
``ticks_per_season`` simulation ticks.
"""

from sim.interfaces.environment import ISeasonStrategy


class SeasonStrategy(ISeasonStrategy):
    SEASONS = ("spring", "summer", "autumn", "winter")

    def __init__(self, ticks_per_season: int = 1200):
        if ticks_per_season <= 0:
            raise ValueError("ticks_per_season must be positive")
        self._ticks_per_season = ticks_per_season

    @property
    def ticks_per_season(self) -> int:
        return self._ticks_per_season

    def get_season(self, tick: int) -> str:
        index = (tick // self._ticks_per_season) % len(self.SEASONS)
        return self.SEASONS[index]
