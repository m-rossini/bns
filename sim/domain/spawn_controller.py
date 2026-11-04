"""Spawn Controller.

Thin orchestrator around a :class:`sim.interfaces.creation.IBeanCreationStrategy`.
The creation strategy decides how many beans exist and drives placement,
gender assignment and instantiation. The controller only wires the already
built strategies together and stores the result on the session.
"""

from __future__ import annotations

from typing import List

from sim.components import GameSession
from sim.domain.beans import Bean
from sim.domain.world import World
from sim.interfaces.creation import IBeanCreationStrategy
from sim.interfaces.gender import IGenderController
from sim.interfaces.placement import IPlacementStrategy, ISpawnController
from sim.observability import get_logger

logger = get_logger("spawn")


class SpawnController(ISpawnController):
    """Run the configured bean creation strategy once."""

    def __init__(
        self,
        world: World,
        session: GameSession,
        creation_strategy: IBeanCreationStrategy,
        placement_strategy: IPlacementStrategy,
        gender_controller: IGenderController,
    ):
        self.world = world
        self.session = session
        self.creation_strategy = creation_strategy
        self.placement = placement_strategy
        self.gender = gender_controller
        self._beans: List[Bean] = []

    def spawn_beans(self) -> List[Bean]:
        """Create the initial population and store it on the session."""
        beans = self.creation_strategy.create_beans(
            self.world, self.placement, self.gender
        )
        self._beans = beans
        self.session.beans = beans
        return beans

    @property
    def beans(self) -> List[Bean]:
        return list(self._beans)
