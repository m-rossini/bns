"""Day/night strategy.

Reads the calendar's time of day and produces:

* ``light_at(x, y, season_factor)`` — sun altitude times smooth local shading
  and the current season's light influence
* ``phase``           — night / dawn / day / dusk
* ``celestial``       — sun and moon arc positions, visibility and moon phase
* ``sky_palette``     — the colours used to blend the sky

Sun and moon have independent speed multipliers and the moon has a phase
offset, so they are not locked to a single global cycle. Every threshold and
shading amplitude comes from `DayNightConfig`, so alternate day/night
implementations can stay presentation-compatible.
"""

import math

from sim.config import DayNightConfig
from sim.domain.visuals import CelestialState, SkyPalette
from sim.interfaces.environment import ICalendar, IDayNightStrategy
from sim.observability import get_logger

logger = get_logger("daynight")


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
    def _altitude(fraction: float) -> float:
        """0.0 at midnight, 1.0 at noon."""
        return 0.5 - 0.5 * math.cos(2.0 * math.pi * fraction)

    def _season_multiplier(self, season_factor: float) -> float:
        """Apply the season's light influence with the configured strength."""
        strength = _clamp(self._config.season_light_influence, 0.0, 1.0)
        return 1.0 + (season_factor - 1.0) * strength

    def light_at(
        self, calendar: ICalendar, x: float, y: float, season_factor: float = 1.0
    ) -> float:
        cfg = self._config
        sun = self._altitude(self._sun_fraction(calendar))

        # Smooth local shading: gentle terrain/cover variation, strongest when
        # the sun is up, so night stays dark everywhere.
        scale_x = max(1.0, cfg.shading_scale_x)
        scale_y = max(1.0, cfg.shading_scale_y)
        local = 0.5 + 0.5 * math.sin(x / scale_x) * math.cos(y / scale_y)
        shade = 1.0 - _clamp(cfg.local_shading, 0.0, 1.0) * local

        seasonal = self._season_multiplier(season_factor)
        return _clamp(sun * shade * seasonal)

    def phase(self, calendar: ICalendar) -> str:
        cfg = self._config
        light = self._altitude(self._sun_fraction(calendar))
        if light < cfg.night_threshold:
            return "night"
        if light < cfg.twilight_threshold:
            return "dawn" if self._sun_fraction(calendar) < 0.5 else "dusk"
        return "day"

    def celestial(self, calendar: ICalendar) -> CelestialState:
        cfg = self._config
        sun_fraction = self._sun_fraction(calendar)
        moon_fraction = self._moon_fraction(calendar)
        sun_visible = cfg.sun_arc_start <= sun_fraction <= cfg.sun_arc_end
        moon_visible = not sun_visible

        # 0.0 = new moon, 0.5 = full moon, 1.0 = new moon again.
        illumination = 0.5 * (1.0 - math.cos(2.0 * math.pi * moon_fraction))
        span = max(1e-6, cfg.sun_arc_end - cfg.sun_arc_start)

        return CelestialState(
            sun_progress=(
                (sun_fraction - cfg.sun_arc_start) / span if sun_visible else 0.0
            ),
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
