"""Interface for the gender controller.

Assigns gender identity and visual color metadata to each bean position.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Tuple

from sim.domain.beans import Position

#: A gender assignment: (position, gender_name, color_rgb).
GenderAssignment = Tuple[Position, str, Tuple[int, int, int]]


class IGenderController(ABC):
    """Assign gender identity + visual color to each bean position."""

    @property
    @abstractmethod
    def gender_names(self) -> Tuple[str, ...]:
        """Ordered list of gender identities (must match config keys)."""

    @abstractmethod
    def assign_attributes(
        self, positions: List[Position]
    ) -> List[GenderAssignment]:
        """Return ``(position, gender, color)`` triples for each position."""
