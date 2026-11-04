"""Bean movement strategies.

Each module implements :class:`sim.interfaces.movement.IMovementStrategy`.
Available strategies (by name):

* ``straight_line`` - global direction + speed, bounce on world edges
"""

from sim.implementations.movement.straight_line import StraightLineMovementStrategy

__all__ = [
    "StraightLineMovementStrategy",
]
