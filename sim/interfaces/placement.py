"""Interfaces for bean placement and spawn orchestration.

The system decouples **position generation** (placement strategies, this
module) from **gender & visual attribute assignment** (gender controller,
:class:`sim.interfaces.gender.IGenderController`). A central
:class:`ISpawnController` orchestrates both.

All placement strategies conform to a uniform interface registered in
configuration; a single setting selects the active algorithm.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from sim.domain.beans import Bean
from sim.domain.world import World

#: A world position in world units (x, y).
Position = Tuple[float, float]


class IPlacementStrategy(ABC):
    """Generate N positions within world bounds, collision-free.

    The same strategies position beans and food morsels: the caller passes
    its own collision radius (bean radius or morsel radius) and the list of
    already-placed objects. All generated positions are guaranteed
    **collision-free**: no two positions overlap, none overlaps a barrier,
    and every position fits inside the world bounds (accounting for the
    radius). Implementations receive the world and the list of already-placed
    objects so they can reject colliding candidates and retry.

    Implementations receive the calculated target count ``n`` plus the world
    bounds and return exactly ``n`` (or as close as achievable) distinct
    coordinates.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy identifier used for config selection."""

    @abstractmethod
    def generate_positions(
        self,
        n: int,
        width: float,
        height: float,
        world: Optional[World] = None,
        existing: Optional[List] = None,
        radius: float = 0.0,
    ) -> List[Position]:
        """Return ``n`` (x, y) positions inside the world bounds.

        Every returned position is collision-free against barriers, the world
        border, and any already-placed objects (``existing`` plus positions
        placed earlier in this same call). ``existing`` entries may be beans,
        morsels, or plain ``(x, y)`` tuples.
        """


class ISpawnController(ABC):
    """Orchestrator: configure, calculate population, place beans, assign gender."""

    @abstractmethod
    def spawn_beans(self) -> List["Bean"]:
        """Run the full placement pipeline and return instantiated beans."""
