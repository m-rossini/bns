"""Gender Controller.

Assigns gender identity and visual color to each bean position based on
configured ratio allocations. Enforces the strict rule that all gender
percentages sum exactly to 100%.

The assignment is randomly shuffled and mapped 1-to-1 onto positions so
that identical biological types are balanced across space without
sequential clustering.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

from sim.config import BeanPlacementConfig
from sim.domain.beans import Position
from sim.interfaces.gender import GenderAssignment, IGenderController
from sim.observability import get_logger

logger = get_logger("gender")


class GenderController(IGenderController):
    """Balanced gender assignment with visual color metadata."""

    def __init__(self, config: BeanPlacementConfig):
        self.config = config
        self._ratios = dict(config.gender_ratios)
        self._colors = dict(config.gender_colors)

        # Validate ratios sum to 100 (defensive; config also validates).
        total = sum(self._ratios.values())
        if abs(total - 100.0) > 1e-6:
            raise ValueError(
                f"GenderController ratios must sum to 100, got {total}"
            )

        self._validate_colors()

    def _validate_colors(self) -> None:
        for gender in self._ratios:
            if gender not in self._colors:
                raise ValueError(
                    f"GenderController missing color for gender {gender!r}"
                )

    @property
    def gender_names(self) -> Tuple[str, ...]:
        return tuple(self._ratios.keys())

    # ------------------------------------------------------------------
    # Quota calculation
    # ------------------------------------------------------------------
    def _quotas(self, total: int) -> Dict[str, int]:
        """Exact per-gender counts summing to ``total``.

        Uses largest-remainder method so rounding never loses/gains beans.
        """
        quotas: Dict[str, int] = {}
        remaining = total
        # Raw fractional counts.
        raw: Dict[str, float] = {}
        for gender, pct in self._ratios.items():
            raw[gender] = total * pct / 100.0
            quotas[gender] = int(math.floor(raw[gender]))
            remaining -= quotas[gender]

        # Distribute leftover beans by largest fractional remainder.
        remainders = sorted(
            self._ratios.keys(),
            key=lambda g: raw[g] - quotas[g],
            reverse=True,
        )
        for gender in remainders[:remaining]:
            quotas[gender] += 1

        return quotas

    # ------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------
    def assign_attributes(
        self, positions: List[Position]
    ) -> List[GenderAssignment]:
        """Return ``(position, gender, color)`` triples (shuffled)."""
        total = len(positions)
        if total == 0:
            return []

        quotas = self._quotas(total)

        # Build sequential pool: [gender, gender, ...] per quota.
        pool: List[str] = []
        for gender in self.gender_names:
            pool.extend([gender] * quotas[gender])

        # Stochastic shuffle so genders are balanced spatially.
        rng = random.Random(sum(ord(c) for g in self.gender_names for c in g))
        rng.shuffle(pool)

        assignments: List[GenderAssignment] = []
        for position, gender in zip(positions, pool):
            color = self._colors[gender]
            assignments.append((position, gender, color))

        return assignments

    @property
    def colors(self) -> Dict[str, Tuple[int, int, int]]:
        return dict(self._colors)
