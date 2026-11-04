"""Bean creation strategies.

Each module implements :class:`sim.interfaces.creation.IBeanCreationStrategy`.
Available strategies (by name):

* ``density_based`` - current behaviour: area × density × variance
* ``fixed_amount``  - exact configured population, independent of area
"""

from sim.implementations.creation.density_based import DensityBasedCreationStrategy
from sim.implementations.creation.fixed_amount import FixedAmountCreationStrategy

__all__ = [
    "DensityBasedCreationStrategy",
    "FixedAmountCreationStrategy",
]
