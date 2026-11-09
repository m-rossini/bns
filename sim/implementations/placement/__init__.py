"""Placement strategies shared by beans and food morsels.

Each module implements :class:`sim.interfaces.placement.IPlacementStrategy`.
The same strategies position both beans and food morsels; the caller passes
its own config (``BeanPlacementConfig`` or ``FoodPlacementConfig``) and the
collision radius (bean radius or morsel radius). Available strategies (by
name):

* ``poisson_disc``      - organic semi-random with minimum spacing
* ``symmetrical``       - rotational/mirror symmetry across axes
* ``colony_cluster``    - clustered colonies around mother centroids
* ``center_to_border``  - core-heavy radial (dense center)
* ``border_to_center``  - periphery-heavy ring (empty center)
* ``linear_gradient``   - directional density bias
* ``resource_gradient`` - noise heatmap around hotspots
"""

from sim.config import PLACEMENT_STRATEGY_NAMES
from sim.implementations.placement.border_to_center import BorderToCenterStrategy
from sim.implementations.placement.center_to_border import CenterToBorderStrategy
from sim.implementations.placement.colony_cluster import ColonyClusterStrategy
from sim.implementations.placement.linear_gradient import LinearGradientStrategy
from sim.implementations.placement.poisson_disc import PoissonDiscStrategy
from sim.implementations.placement.resource_gradient import ResourceGradientStrategy
from sim.implementations.placement.symmetrical import SymmetricalStrategy
from sim.interfaces.placement import IPlacementStrategy

__all__ = [
    "BorderToCenterStrategy",
    "CenterToBorderStrategy",
    "ColonyClusterStrategy",
    "LinearGradientStrategy",
    "PoissonDiscStrategy",
    "ResourceGradientStrategy",
    "SymmetricalStrategy",
    "build_placement_strategy",
]

#: Name -> strategy class wiring. The valid names live in
#: ``config.PLACEMENT_STRATEGY_NAMES``.
_PLACEMENT_CLASSES = {
    "poisson_disc": PoissonDiscStrategy,
    "symmetrical": SymmetricalStrategy,
    "colony_cluster": ColonyClusterStrategy,
    "center_to_border": CenterToBorderStrategy,
    "border_to_center": BorderToCenterStrategy,
    "linear_gradient": LinearGradientStrategy,
    "resource_gradient": ResourceGradientStrategy,
}


def build_placement_strategy(config) -> IPlacementStrategy:
    """Build the placement strategy selected by a placement config.

    ``config`` may be a :class:`sim.config.BeanPlacementConfig` or a
    :class:`sim.config.FoodPlacementConfig`; both expose ``strategy_name``,
    ``seed`` and ``strategy_config()``.
    """
    name = config.strategy_name
    cls = _PLACEMENT_CLASSES.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown placement strategy {name!r}. "
            f"Use one of: {sorted(PLACEMENT_STRATEGY_NAMES)}"
        )
    return cls(config=config.strategy_config(name), seed=config.seed)
