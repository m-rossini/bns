"""Energy strategy interface for bean energy replenishment."""

from __future__ import annotations

from typing import Dict, List, Optional

from sim.domain.beans import Bean
from sim.interfaces.world import IWorld
from sim.domain.environment import Environment


class IEnergyStrategy:
    """Interface for energy replenishment strategies.

    Determines how much energy each bean gains per tick based on
    environment, genotype, and phenotype.
    """

    def calculate_energy_gain(
        self,
        beans: List[Bean],
        environment: Optional[Environment],
        world: Optional[IWorld],
        dt: float,
    ) -> Dict[int, float]:
        """
        Calculate energy gain for each bean.

        Args:
            beans: All beans in the simulation
            environment: Current environment (light, temperature, resources)
            world: World reference for spatial queries
            dt: Time delta in seconds

        Returns:
            Dict mapping bean.id -> energy gain amount
        """
        raise NotImplementedError