"""Day/night strategy.

Reads the calendar's time of day and produces:

* ``light_at(x, y)``  — sun altitude times a smooth local shading term
* ``phase``           — night / dawn / day / dusk
* ``celestial``       — sun and moon arc positions, visibility and moon phase
* ``sky_palette``     — the colours used to blend the sky

Sun and moon have independent speed multipliers and the moon has a phase
offset, so they are not locked to a single global cycle.
"""

import math

from sim.config import DayNightConfig
from sim.domain.visuals import CelestialState, SkyPalette
from sim.interfaces.environment import ICalendar, IDayNightStrategy


class DayNightStrategy(IDayNightStrategy):
    def __init__(self, config: DayNightConfig, ticks_per_day: int):
        if ticks_per_day <= 0:
            raise ValueError("ticks_per_day must be positive")
        self._config = config
        self._ticks_per_day = ticks_per_day

    @property
    def ticks_per_day(self) -> int:
        return self._ticks_per_day

    # ------------------------------------------------------------------
    # Sun / moon
    # ------------------------------------------------------------------
    def _sun_fraction(self, calendar: ICalendar) -> float:
        """Position of the sun in its cycle: 0.0 = midnight, 0.5 = noon."""
        return (calendar.day_fraction * self._config.sun_speed) % 1.0

    def _moon_fraction(self, calendar: ICalendar) -> float:
        return (
            calendar.day_fraction * self._config.moon_speed
            + self._config.moon_phase_offset
        ) % 1.0

    @staticmethod
    def _altitude(fraction: float) -> float:
        """0.0 at midnight, 1.0 at noon."""
        return 0.5 - 0.5 * math.cos(2.0 * math.pi * fraction)

    def light_at(self, calendar: ICalendar, x: float, y: float) -> float:
        sun = self._altitude(self._sun_fraction(calendar))

        # Smooth local shading: gentle terrain/cover variation, strongest when
        # the sun is up, so night stays dark everywhere.
        local = 0.5 + 0.5 * math.sin(x / 190.0) * math.cos(y / 150.0)
        shade = 1.0 - 0.10 * local

        return max(0.0, min(1.0, sun * shade))

    def phase(self, calendar: ICalendar) -> str:
        light = self._altitude(self._sun_fraction(calendar))
        if light < 0.12:
            return "night"
        if light < 0.45:
            return "dawn" if self._sun_fraction(calendar) < 0.5 else "dusk"
        return "day"

    def celestial(self, calendar: ICalendar) -> CelestialState:
        sun_fraction = self._sun_fraction(calendar)
        moon_fraction = self._moon_fraction(calendar)
        sun_visible = 0.25 <= sun_fraction <= 0.75
        moon_visible = not sun_visible

        # 0.0 = new moon, 0.5 = full moon, 1.0 = new moon again.
        illumination = 0.5 * (1.0 - math.cos(2.0 * math.pi * moon_fraction))

        return CelestialState(
            sun_progress=(sun_fraction - 0.25) / 0.5 if sun_visible else 0.0,
            moon_progress=((moon_fraction + 0.25) % 1.0),
            sun_visible=sun_visible,
            moon_visible=moon_visible,
            moon_illumination=illumination,
        )

    def sky_palette(self) -> SkyPalette:
        cfg = self._config
        return SkyPalette(
            night=cfg.night_sky,
            day=cfg.day_sky,
            twilight=cfg.twilight_sky,
            overcast=cfg.overcast_sky,
            sun=cfg.sun_color,
            moon=cfg.moon_color,
            star=cfg.star_color,
        )
