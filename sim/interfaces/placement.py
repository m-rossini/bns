"""Interfaces for bean placement and gender assignment.

The system decouples **position generation** (placement strategies) from
**gender & visual attribute assignment** (gender controller). A central
:class:`ISpawnController` orchestrates both.

All placement strategies and gender controllers conform to uniform interfaces
registered in configuration; a single setting selects the active algorithm.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from sim.domain.beans import Bean
from sim.domain.world import World

#: A world position in world units (x, y).
Position = Tuple[float, float]


class IPlacementStrategy(ABC):
    """Generate N initial bean positions within world bounds.

    All generated positions are guaranteed **collision-free**: no two beans
    overlap, no bean overlaps a barrier, and every bean fits inside the world
    bounds (accounting for its radius). Implementations receive the world and
    the list of already-placed beans so they can reject colliding candidates
    and retry.

    Implementations receive the calculated target population ``n`` plus the
    world bounds and return exactly ``n`` (or as close as achievable)
    distinct coordinates.
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
        existing: Optional[List[Bean]] = None,
        radius: float = 0.0,
    ) -> List[Position]:
        """Return ``n`` (x, y) positions inside the world bounds.

        Every returned position is collision-free against barriers, the world
        border, and any already-placed beans (``existing`` plus beans placed
        earlier in this same call).
        """


class IGenderController(ABC):
    """Assign gender identity + visual color to each bean position."""

    @property
    @abstractmethod
    def gender_names(self) -> Tuple[str, ...]:
        """Ordered list of gender identities (must match config keys)."""

    @abstractmethod
    def assign_attributes(
        self, positions: List[Position]
    ) -> List[Tuple[Position, str, Tuple[int, int, int]]]:
        """Return ``(position, gender, color)`` triples for each position."""


class ISpawnController(ABC):
    """Orchestrator: configure, calculate population, place beans, assign gender."""

    @abstractmethod
    def spawn_beans(self) -> List["Bean"]:
        """Run the full placement pipeline and return instantiated beans."""
