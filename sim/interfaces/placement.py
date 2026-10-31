"""Interfaces for bean placement and gender assignment.

The system decouples **position generation** (placement strategies) from
**gender & visual attribute assignment** (gender controller). A central
:class:`ISpawnController` orchestrates both.

All placement strategies and gender controllers conform to uniform interfaces
registered in configuration; a single setting selects the active algorithm.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Tuple

from sim.domain.beans import Bean

#: A world position in world units (x, y).
Position = Tuple[float, float]


class IPlacementStrategy(ABC):
    """Generate N initial bean positions within world bounds.

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
        self, n: int, width: float, height: float
    ) -> List[Position]:
        """Return ``n`` (x, y) positions inside the world bounds."""


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
