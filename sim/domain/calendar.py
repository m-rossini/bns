"""Tick -> date conversion.

The calendar is the single time authority. Seasons and the day/night cycle are
siblings that both read it; neither one owns the other.

Conventions:
* one day is ``ticks_per_day`` ticks, starting at 00:00 (fraction 0.0)
* one season is ``ticks_per_season`` ticks and holds ``ticks_per_season //
  ticks_per_day`` days
* seasons cycle through the configured names; after the last one, year + 1
"""

from typing import Sequence, Tuple


class Calendar:
    def __init__(
        self,
        ticks_per_day: int,
        ticks_per_season: int,
        season_names: Sequence[str],
        start_tick: int = 0,
    ):
        if ticks_per_day <= 0:
            raise ValueError("ticks_per_day must be positive")
        if ticks_per_season <= 0:
            raise ValueError("ticks_per_season must be positive")
        if not season_names:
            raise ValueError("at least one season name is required")

        self._ticks_per_day = ticks_per_day
        self._ticks_per_season = ticks_per_season
        self._season_names: Tuple[str, ...] = tuple(season_names)
        self._tick = max(0, start_tick)

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------
    @property
    def tick(self) -> int:
        return self._tick

    @tick.setter
    def tick(self, value: int) -> None:
        self._tick = max(0, int(value))

    def advance(self, ticks: int = 1) -> None:
        self._tick = max(0, self._tick + ticks)

    # ------------------------------------------------------------------
    # Day / clock
    # ------------------------------------------------------------------
    @property
    def ticks_per_day(self) -> int:
        return self._ticks_per_day

    @property
    def ticks_per_season(self) -> int:
        return self._ticks_per_season

    @property
    def day(self) -> int:
        """1-based day counter since the start of the run."""
        return self._tick // self._ticks_per_day + 1

    @property
    def day_fraction(self) -> float:
        """0.0 = midnight, 0.5 = noon."""
        return (self._tick % self._ticks_per_day) / self._ticks_per_day

    @property
    def hour(self) -> int:
        return int(self.day_fraction * 24.0) % 24

    @property
    def minute(self) -> int:
        hours = self.day_fraction * 24.0
        return int((hours - int(hours)) * 60)

    @property
    def clock(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"

    # ------------------------------------------------------------------
    # Season / year
    # ------------------------------------------------------------------
    @property
    def season_names(self) -> Tuple[str, ...]:
        return self._season_names

    @property
    def season_index(self) -> int:
        return (self._tick // self._ticks_per_season) % len(self._season_names)

    @property
    def season(self) -> str:
        return self._season_names[self.season_index]

    @property
    def season_progress(self) -> float:
        return (self._tick % self._ticks_per_season) / self._ticks_per_season

    @property
    def day_of_season(self) -> int:
        offset = self._tick % self._ticks_per_season
        return offset // self._ticks_per_day + 1

    @property
    def days_per_season(self) -> int:
        return max(1, self._ticks_per_season // self._ticks_per_day)

    @property
    def year(self) -> int:
        cycle = self._ticks_per_season * len(self._season_names)
        return self._tick // cycle + 1

    def reset(self) -> None:
        self._tick = 0
