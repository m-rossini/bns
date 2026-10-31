"""Bean placement strategies.

Each module implements :class:`sim.interfaces.placement.IPlacementStrategy`.
Available strategies (by name):

* ``poisson_disc``      - organic semi-random with minimum spacing
* ``symmetrical``       - rotational/mirror symmetry across axes
* ``colony_cluster``    - clustered colonies around mother centroids
* ``center_to_border``  - core-heavy radial (dense center)
* ``border_to_center``  - periphery-heavy ring (empty center)
* ``linear_gradient``   - directional density bias
* ``resource_gradient`` - noise heatmap around hotspots
"""

from sim.implementations.placement.border_to_center import BorderToCenterStrategy
from sim.implementations.placement.center_to_border import CenterToBorderStrategy
from sim.implementations.placement.colony_cluster import ColonyClusterStrategy
from sim.implementations.placement.linear_gradient import LinearGradientStrategy
from sim.implementations.placement.poisson_disc import PoissonDiscStrategy
from sim.implementations.placement.resource_gradient import ResourceGradientStrategy
from sim.implementations.placement.symmetrical import SymmetricalStrategy

__all__ = [
    "BorderToCenterStrategy",
    "CenterToBorderStrategy",
    "ColonyClusterStrategy",
    "LinearGradientStrategy",
    "PoissonDiscStrategy",
    "ResourceGradientStrategy",
    "SymmetricalStrategy",
]
