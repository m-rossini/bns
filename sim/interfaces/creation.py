"""Interface for bean creation strategies.

A creation strategy decides *how many* beans the initial population has and
drives the pipeline that produces them:

1. ask the configured placement strategy for positions,
2. ask the configured gender controller for gender + colour,
3. draw a genotype per bean from the configured ranges and seed,
4. instantiate each bean with its genotype + phenotype.

The creation strategy **receives** the placement strategy and gender
controller; it never constructs them itself. That keeps the composition in the
DI container and lets configuration swap any part independently.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import List, Optional

from sim.domain.beans import Bean
from sim.domain.world import World
from sim.interfaces.gender import IGenderController
from sim.interfaces.placement import IPlacementStrategy

from sim.config import GenotypeConfig


class IBeanCreationStrategy(ABC):
    """Create the initial bean population."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy identifier used for config selection."""

    @abstractmethod
    def create_beans(
        self,
        world: World,
        placement_strategy: IPlacementStrategy,
        gender_controller: IGenderController,
        genotype_ranges: Optional[GenotypeConfig] = None,
        genotype_seed: int = 0,
    ) -> List[Bean]:
        """Return the created beans for the given world."""
