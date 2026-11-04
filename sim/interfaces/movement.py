"""Interface for bean movement strategies.

A movement strategy owns *how* beans move. The engine owns *when*: it calls
:meth:`IMovementStrategy.update` once per simulation tick while the session is
playing.

Beans are updated in place. Their ``id`` stays stable for the whole lifetime of
the simulation, so collision events can reference the same bean across ticks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from sim.domain.beans import Bean
from sim.interfaces.world import IWorld


class IMovementStrategy(ABC):
    """Move every bean by one simulation tick."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy identifier used for config selection."""

    @abstractmethod
    def update(self, beans: Sequence[Bean], world: IWorld, dt: float) -> None:
        """Advance every bean by ``dt`` seconds, in place."""
