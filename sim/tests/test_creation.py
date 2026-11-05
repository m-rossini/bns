"""Tests for bean creation strategies."""

import pytest

from sim.config import (
    BeanPlacementConfig,
    CreationConfig,
    FixedAmountCreationConfig,
    MovementConfig,
    PoissonDiscConfig,
    SeasonConfig,
    SimulationConfig,
    WorldConfig,
)
from sim.container import Container
from sim.domain.world import World
from sim.implementations.creation import (
    DensityBasedCreationStrategy,
    FixedAmountCreationStrategy,
)
from sim.implementations.gender import GenderController
from sim.interfaces.placement import IPlacementStrategy


class RecordingPlacement(IPlacementStrategy):
    """Deterministic placement stub that hands out a fixed position list."""

    name = "recording"

    def __init__(self, positions):
        self.positions = list(positions)
        self.calls = []

    def generate_positions(
        self, n, width, height, world=None, existing=None, radius=0.0
    ):
        already = len(existing or [])
        self.calls.append((n, already, radius))
        return self.positions[already:already + n]


def _placement_config(**overrides) -> BeanPlacementConfig:
    data = dict(
        strategy_name="poisson_disc",
        density_tier="average",
        variance=0.0,
        seed=42,
        gender_ratios={"male": 50.0, "female": 50.0},
        gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
        bean_radius=2.0,
        poisson_disc=PoissonDiscConfig(),
    )
    data.update(overrides)
    return BeanPlacementConfig(**data)


def test_fixed_amount_creates_exactly_the_configured_total():
    world = World(width=200.0, height=200.0, cell_size=10.0)
    placement = RecordingPlacement([(10.0 + i, 20.0) for i in range(30)])
    strategy = FixedAmountCreationStrategy(
        FixedAmountCreationConfig(total_beans=25),
        _placement_config(),
    )

    beans = strategy.create_beans(world, placement, GenderController(_placement_config()))

    assert len(beans) == 25
    assert [b.id for b in beans] == list(range(1, 26))
    assert placement.calls[0][1] == 0
    assert placement.calls[0][0] >= 25


def test_fixed_amount_never_exceeds_the_total_and_fills_in_batches():
    world = World(width=200.0, height=200.0, cell_size=10.0)
    # First batch only yields 10, so the strategy asks for the remaining 15.
    placement = RecordingPlacement([(i * 3.0 + 1.0, 10.0) for i in range(40)])
    original = placement.generate_positions

    calls = {"n": 0}

    def trickle(n, width, height, world=None, existing=None, radius=0.0):
        calls["n"] += 1
        already = len(existing or [])
        limit = 10 if calls["n"] == 1 else n
        self_positions = placement.positions[already:already + min(n, limit)]
        return self_positions

    placement.generate_positions = trickle
    strategy = FixedAmountCreationStrategy(
        FixedAmountCreationConfig(total_beans=25),
        _placement_config(),
    )

    beans = strategy.create_beans(world, placement, GenderController(_placement_config()))

    assert len(beans) == 25
    assert calls["n"] >= 2


def test_fixed_amount_shortfall_is_capped_not_exceeded():
    world = World(width=200.0, height=200.0, cell_size=10.0)
    placement = RecordingPlacement([(5.0, 5.0)] * 3)
    strategy = FixedAmountCreationStrategy(
        FixedAmountCreationConfig(total_beans=10),
        _placement_config(),
    )

    beans = strategy.create_beans(world, placement, GenderController(_placement_config()))

    assert len(beans) == 3


def test_density_based_uses_the_area_formula():
    world = World(width=100.0, height=100.0, cell_size=10.0)
    placement = RecordingPlacement([(float(i), 1.0) for i in range(5000)])
    cfg = _placement_config(density_tier="average", variance=0.0, seed=1)
    strategy = DensityBasedCreationStrategy(cfg)

    beans = strategy.create_beans(world, placement, GenderController(cfg))

    area = 100.0 * 100.0
    expected = round(area * 0.0020)  # density coefficient for "average"
    assert len(beans) == expected


def test_container_uses_fixed_amount_creation_strategy():
    config = SimulationConfig(
        world=WorldConfig(width=300.0, height=300.0, cell_size=10.0),
        bean_placement=_placement_config(),
        creation=CreationConfig(
            strategy_name="fixed_amount",
            fixed_amount=FixedAmountCreationConfig(total_beans=20),
        ),
        seasons=[SeasonConfig(name="Spring")],
    )
    container = Container(config)

    assert len(container.beans) <= 20
    assert all(bean.id > 0 for bean in container.beans)


def test_fixed_amount_config_rejects_negative_total():
    with pytest.raises(ValueError):
        FixedAmountCreationConfig(total_beans=-1)


def test_creation_config_rejects_unknown_strategy():
    with pytest.raises(ValueError):
        CreationConfig(strategy_name="does_not_exist")


def test_movement_config_rejects_zero_direction_and_negative_speed():
    with pytest.raises(ValueError):
        MovementConfig(direction=(0.0, 0.0))
    with pytest.raises(ValueError):
        MovementConfig(speed=-1.0)
    with pytest.raises(ValueError):
        MovementConfig(strategy_name="does_not_exist")
