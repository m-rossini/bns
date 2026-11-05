"""Fixed energy gain strategy - constant energy per tick from config."""

from __future__ import annotations

from typing import Dict, List, Optional

from sim.config import EnergyConfig
from sim.domain.beans import Bean
from sim.domain.environment import Environment
from sim.interfaces.energy import IEnergyStrategy
from sim.interfaces.world import IWorld
from sim.observability import get_logger

logger = get_logger("energy.fixed")


class FixedEnergyStrategy(IEnergyStrategy):
    """Fixed energy gain per tick, configurable via EnergyConfig."""

    name = "fixed"

    def __init__(self, config: EnergyConfig):
        self.config = config

    def calculate_energy_gain(
        self,
        beans: List[Bean],
        environment: Optional[Environment],
        world: Optional[IWorld],
        dt: float,
    ) -> Dict[int, float]:
        """Return fixed energy gain for all non-dormant beans."""
        if self.config.energy_per_tick <= 0.0:
            return {}

        gains = {}
        for bean in beans:
            if bean.phenotype is None or bean.phenotype.is_dormant:
                continue
            gains[bean.id] = self.config.energy_per_tick * dt
        return gains


class PerDayEnergyStrategy(IEnergyStrategy):
    """Lump sum energy gain at day boundaries."""

    name = "per_day"

    def __init__(self, config: EnergyConfig):
        self.config = config
        self._last_day_tick = -1

    def calculate_energy_gain(
        self,
        beans: List[Bean],
        environment: Optional[Environment],
        world: Optional[IWorld],
        dt: float,
    ) -> Dict[int, float]:
        """Give energy only at day boundaries."""
        if environment is None or environment.calendar is None:
            return {}

        current_day = environment.calendar.day
        if current_day == self._last_day_tick:
            return {}

        self._last_day_tick = current_day

        gains = {}
        for bean in beans:
            if bean.phenotype is None:
                continue
            gains[bean.id] = self.config.energy_per_day
        return gains