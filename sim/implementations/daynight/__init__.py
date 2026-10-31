"""Day/night strategy.

Reads the calendar's time of day **and the season's solar profile** and
produces:

* ``light_at(x, y, solar)`` — sun arc * peak intensity * local shading
* ``phase``           — night / dawn / day / dusk
* ``celestial``       — sun and moon arc positions, visibility and moon phase
* ``sky_palette``     — the colours used to blend the sky

The amount of sun (how bright noon is and how long the day lasts) is owned by
the season strategy and arrives as a `SolarProfile`. This strategy only shapes
it: it places the sun inside the season's daylight window, applies the smooth
terrain shading and derives the sky phase.

Sun and moon have independent speed multipliers and the moon has a phase
offset, so they are not locked to a single global cycle. Every threshold and
shading amplitude comes from `DayNightConfig`, so alternate day/night
implementations can stay presentation-compatible.
"""

import math
from typing import Optional

from sim.config import DayNightConfig
from sim.domain.visuals import CelestialState, SkyPalette, SolarProfile
from sim.interfaces.environment import ICalendar, IDayNightStrategy
from sim.observability import get_logger

logger = get_logger("daynight")

_NEUTRAL_SOLAR = SolarProfile()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


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
    def _daylight_window(solar: SolarProfile):
        """(start, end) of the daylight window as day fractions."""
        daylight = _clamp(solar.daylight_fraction, 0.05, 1.0)
        start = 0.5 - daylight / 2.0
        return start, start + daylight

    def _sun_arc(self, calendar: ICalendar, solar: SolarProfile) -> float:
        """Sun altitude 0..1 for the season's day length, 0 at night."""
        start, end = self._daylight_window(solar)
        fraction = self._sun_fraction(calendar)
        if fraction <= start or fraction >= end:
            return 0.0
        position = (fraction - start) / max(1e-6, end - start)
        return math.sin(math.pi * position)

    def light_at(
        self,
        calendar: ICalendar,
        x: float,
        y: float,
        solar: Optional[SolarProfile] = None,
    ) -> float:
        cfg = self._config
        solar = solar or _NEUTRAL_SOLAR
        arc = self._sun_arc(calendar, solar)

        # Smooth local shading: gentle terrain/cover variation, strongest when
        # the sun is up, so night stays dark everywhere.
        scale_x = max(1.0, cfg.shading_scale_x)
        scale_y = max(1.0, cfg.shading_scale_y)
        local = 0.5 + 0.5 * math.sin(x / scale_x) * math.cos(y / scale_y)
        shade = 1.0 - _clamp(cfg.local_shading, 0.0, 1.0) * local

        return _clamp(arc * shade * max(0.0, solar.sun_intensity))

    def phase(
        self, calendar: ICalendar, solar: Optional[SolarProfile] = None
    ) -> str:
        cfg = self._config
        solar = solar or _NEUTRAL_SOLAR
        arc = self._sun_arc(calendar, solar)
        if arc < cfg.night_threshold:
            return "night"
        if arc < cfg.twilight_threshold:
            return "dawn" if self._sun_fraction(calendar) < 0.5 else "dusk"
        return "day"

    def celestial(
        self, calendar: ICalendar, solar: Optional[SolarProfile] = None
    ) -> CelestialState:
        solar = solar or _NEUTRAL_SOLAR
        start, end = self._daylight_window(solar)
        sun_fraction = self._sun_fraction(calendar)
        moon_fraction = self._moon_fraction(calendar)
        sun_visible = start <= sun_fraction <= end
        moon_visible = not sun_visible

        # 0.0 = new moon, 0.5 = full moon, 1.0 = new moon again.
        illumination = 0.5 * (1.0 - math.cos(2.0 * math.pi * moon_fraction))
        span = max(1e-6, end - start)

        return CelestialState(
            sun_progress=_clamp((sun_fraction - start) / span) if sun_visible else 0.0,
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
