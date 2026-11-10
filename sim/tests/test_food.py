"""Behavior tests for the renewable food system.

Food morsels seed a starting energy pool, beans nibble them on contact, and
the strategy tops the level back toward a seasonal target. These tests check
amounts and appetites, not internals.
"""

from __future__ import annotations

import random

import pytest

from sim.components import GameState
from sim.config import (
    BeanPlacementConfig,
    EnergyConfig,
    EnvironmentConfig,
    FoodConfig,
    FoodPlacementConfig,
    GenotypeConfig,
    PoissonDiscConfig,
    SeasonConfig,
    SimulationConfig,
    SymmetricalConfig,
    WorldConfig,
)
from sim.container import Container
from sim.domain.beans import Bean
from sim.domain.food import (
    Food,
    feed_beans_on_food,
    seasonal_abundance,
    total_energy,
)
from sim.domain.genotype import (
    DEFAULT_GENOTYPE,
    create_default_phenotype,
    draw_genotype,
)
from sim.implementations.food import RandomFoodSpawnStrategy
from sim.implementations.placement import build_placement_strategy
from sim.implementations.placement.symmetrical import SymmetricalStrategy
from sim.main import _step
from sim.persistence import (
    load_snapshot,
    restore_snapshot,
    save_snapshot,
)


def _season(**overrides):
    values = dict(
        name="Spring",
        ground_color=(96, 170, 88),
        base_temperature=14.0,
        temperature_swing=7.0,
        humidity=0.55,
        pressure_hpa=1012.0,
        sun_intensity=0.95,
        daylight_fraction=0.50,
        ground_meaning="growing season",
        weather_weights={"clear": 50, "cloudy": 50},
    )
    values.update(overrides)
    return SeasonConfig(**values)


def _make_config(**overrides):
    cfg = SimulationConfig(
        world=WorldConfig(width=200.0, height=200.0, cell_size=10.0),
        seasons=[_season()],
        bean_placement=BeanPlacementConfig(
            strategy_name="poisson_disc",
            density_tier="average",
            variance=0.0,
            seed=42,
            gender_ratios={"male": 50.0, "female": 50.0},
            gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
            bean_radius=2.0,
            poisson_disc=PoissonDiscConfig(),
        ),
        environment=EnvironmentConfig(
            weather_strategy="WeatherStrategy",
            season_strategy="SeasonStrategy",
            daynight_strategy="DayNightStrategy",
        ),
    )
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return cfg


def _bean(bean_id, x, y, energy=100.0, capacity=80.0):
    genotype = DEFAULT_GENOTYPE
    phenotype = create_default_phenotype(genotype)
    phenotype.current_energy = energy
    phenotype.digestion_capacity = capacity
    return Bean(
        id=bean_id,
        x=x,
        y=y,
        gender="female",
        color=genotype.base_color,
        genotype=genotype,
        phenotype=phenotype,
    )


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------


def test_initial_seeding_sums_to_the_configured_amount():
    """Tick-0 morsels add up to the starting pool (within one morsel)."""
    config = FoodConfig(
        initial_total_energy=2000.0,
        min_morsel_energy=20.0,
        max_morsel_energy=200.0,
        seed=11,
    )
    world = Container(_make_config()).world

    foods = RandomFoodSpawnStrategy(config).initial_food(world)

    assert foods
    assert all(20.0 <= food.energy <= 200.0 for food in foods)
    assert all(0.0 <= food.x <= world.width for food in foods)
    assert all(0.0 <= food.y <= world.height for food in foods)
    assert config.initial_total_energy <= total_energy(foods) < \
        config.initial_total_energy + 200.0


def test_container_seeds_food_and_disabled_strategy_seeds_none():
    """The container owns the initial morsels; None disables the system."""
    container = Container(_make_config())

    assert container.session.foods
    assert total_energy(container.session.foods) >= \
        container.config.food.initial_total_energy

    off = Container(_make_config(food=FoodConfig(strategy_name=None)))
    assert off.session.foods == []
    assert off.food_strategy is None


def test_unknown_food_strategy_is_rejected():
    """Config validation pins the name to the implemented set."""
    with pytest.raises(ValueError):
        FoodConfig(strategy_name="buffet")
    with pytest.raises(ValueError):
        FoodConfig(min_morsel_energy=300.0, max_morsel_energy=200.0)


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------


def _assert_clear_of_barriers(foods, world):
    for food in foods:
        for barrier in world.barriers:
            if barrier.kind != "rect":
                continue
            cx = min(max(food.x, barrier.x), barrier.x + barrier.width)
            cy = min(max(food.y, barrier.y), barrier.y + barrier.height)
            dist_sq = (food.x - cx) ** 2 + (food.y - cy) ** 2
            assert dist_sq > food.radius ** 2, (
                f"food {food.id} ({food.x:.1f},{food.y:.1f}) "
                f"overlaps barrier {barrier.id}"
            )


def _assert_no_morsel_overlap(foods):
    for index, first in enumerate(foods):
        for second in foods[index + 1:]:
            dx = first.x - second.x
            dy = first.y - second.y
            min_dist = first.radius + second.radius
            assert dx * dx + dy * dy >= min_dist * min_dist, (
                f"foods {first.id} and {second.id} overlap"
            )


def test_initial_food_never_overlaps_barriers_or_itself():
    """Strategy-placed morsels stay clear of barriers and each other."""
    config = FoodConfig(
        initial_total_energy=2000.0,
        min_morsel_energy=20.0,
        max_morsel_energy=200.0,
        seed=11,
    )
    world = Container(_make_config()).world

    foods = RandomFoodSpawnStrategy(config).initial_food(world)

    assert foods
    _assert_clear_of_barriers(foods, world)
    _assert_no_morsel_overlap(foods)


def test_top_up_never_overlaps_barriers_or_existing_morsels():
    """Top-up morsels use the same collision rules as the initial seeding."""
    config = FoodConfig(
        initial_total_energy=2000.0,
        target_total_energy=2000.0,
        top_up_interval_ticks=10,
        min_morsel_energy=20.0,
        max_morsel_energy=200.0,
        max_items=1000,
        seed=5,
    )
    world = Container(_make_config()).world
    strategy = RandomFoodSpawnStrategy(config)
    foods = strategy.initial_food(world)
    del foods[: len(foods) // 2]

    added = strategy.top_up(foods, world, tick=10, abundance=1.0)

    assert added
    _assert_clear_of_barriers(added, world)
    _assert_no_morsel_overlap(foods + added)


def test_food_placement_config_rejects_unknown_strategy():
    with pytest.raises(ValueError):
        FoodPlacementConfig(strategy_name="buffet")


def test_food_placement_strategy_is_configurable():
    """The container factory builds the strategy named by the config."""
    config = FoodPlacementConfig(
        strategy_name="symmetrical",
        seed=7,
        symmetrical=SymmetricalConfig(symmetry_axes=4),
    )
    strategy = build_placement_strategy(config)
    assert isinstance(strategy, SymmetricalStrategy)
    assert strategy.name == "symmetrical"
    assert strategy.seed == 7


def test_food_placement_seed_is_deterministic():
    kwargs = dict(
        initial_total_energy=500.0,
        min_morsel_energy=20.0,
        max_morsel_energy=200.0,
        seed=3,
        placement=FoodPlacementConfig(strategy_name="poisson_disc", seed=42),
    )
    world = Container(_make_config()).world

    first = RandomFoodSpawnStrategy(FoodConfig(**kwargs)).initial_food(world)
    second = RandomFoodSpawnStrategy(FoodConfig(**kwargs)).initial_food(world)

    assert [(f.x, f.y) for f in first] == [(f.x, f.y) for f in second]


def test_container_uses_configured_food_placement():
    config = _make_config(
        food=FoodConfig(
            initial_total_energy=500.0,
            min_morsel_energy=20.0,
            max_morsel_energy=200.0,
            seed=3,
            placement=FoodPlacementConfig(strategy_name="symmetrical", seed=7),
        )
    )
    container = Container(config)

    assert container.food_strategy is not None
    assert container.food_placement_strategy is not None
    assert container.food_placement_strategy.name == "symmetrical"
    _assert_clear_of_barriers(container.session.foods, container.world)


# ---------------------------------------------------------------------------
# Top-up and seasons
# ---------------------------------------------------------------------------


def test_top_up_only_fires_on_interval_and_covers_the_deficit():
    """Off-interval ticks add nothing; on-interval ticks refill to target."""
    config = FoodConfig(
        initial_total_energy=1000.0,
        target_total_energy=1000.0,
        top_up_interval_ticks=10,
        min_morsel_energy=20.0,
        max_morsel_energy=200.0,
        max_items=1000,
        seed=5,
    )
    world = Container(_make_config()).world
    strategy = RandomFoodSpawnStrategy(config)
    foods = strategy.initial_food(world)
    del foods[: len(foods) // 2]  # simulate a hungry population

    assert strategy.top_up(foods, world, tick=7) == []
    before = total_energy(foods)
    added = strategy.top_up(foods, world, tick=10, abundance=1.0)

    assert added
    assert total_energy(foods + added) >= 1000.0
    assert total_energy(added) <= 1000.0 - before + 200.0
    assert len({food.id for food in foods + added}) == len(foods) + len(added)


def test_top_up_stays_quiet_above_target_and_respects_max_items():
    """No deficit means no morsels; the item cap is never exceeded."""
    config = FoodConfig(
        target_total_energy=100.0,
        top_up_interval_ticks=10,
        max_items=3,
        seed=5,
    )
    world = Container(_make_config()).world
    strategy = RandomFoodSpawnStrategy(config)

    rich = [
        Food(id=1, x=10.0, y=10.0, radius=4.0, energy=500.0,
             initial_energy=500.0)
    ]
    assert strategy.top_up(rich, world, tick=10) == []

    assert len(strategy.initial_food(world)) <= 3


def test_winter_grows_less_food_than_summer():
    """The seasonal multiplier orders effective targets across the year."""
    winter = seasonal_abundance(0.55, 0.34)
    spring = seasonal_abundance(0.95, 0.50)
    summer = seasonal_abundance(1.15, 0.60)

    assert winter < spring < summer
    assert 0.15 <= winter and summer <= 1.6


# ---------------------------------------------------------------------------
# Nibbling
# ---------------------------------------------------------------------------


def test_nibble_is_capped_by_appetite_and_leaves_a_remainder():
    """A bean takes at most its digestion capacity; the rest stays."""
    bean = _bean(1, 10.0, 10.0, energy=100.0, capacity=30.0)
    foods = [
        Food(id=1, x=10.0, y=10.0, radius=4.0, energy=200.0,
             initial_energy=200.0)
    ]

    contacts = feed_beans_on_food([bean], foods, bean_radius=2.0)

    assert contacts == 1
    assert bean.phenotype.energy_eaten_total == 30.0
    assert foods[0].energy == 170.0  # remainder for later visits


def test_absorbed_energy_is_scaled_by_efficiency_and_counters_diverge():
    """Eaten is what leaves the morsel; absorbed is what the bean keeps."""
    bean = _bean(1, 10.0, 10.0, energy=100.0, capacity=500.0)
    bean.phenotype.efficiency = 0.5
    foods = [
        Food(id=1, x=10.0, y=10.0, radius=4.0, energy=60.0,
             initial_energy=60.0)
    ]

    feed_beans_on_food([bean], foods, bean_radius=2.0)

    assert bean.phenotype.energy_eaten_total == 60.0
    assert bean.phenotype.energy_absorbed_total == 30.0
    assert foods[0].energy == 0.0


def test_full_and_dead_beans_take_nothing():
    """No room or no life means no contact."""
    full = _bean(1, 10.0, 10.0, energy=DEFAULT_GENOTYPE.energy_capacity)
    dead = _bean(2, 10.0, 10.0, energy=0.0)
    foods = [
        Food(id=1, x=10.0, y=10.0, radius=4.0, energy=100.0,
             initial_energy=100.0)
    ]

    assert feed_beans_on_food([full, dead], foods, bean_radius=2.0) == 0
    assert foods[0].energy == 100.0


# ---------------------------------------------------------------------------
# Genes and snapshots
# ---------------------------------------------------------------------------


def test_appetite_is_drawn_per_bean_from_its_range():
    """digestion_capacity is a ranged gene like every other gene."""
    ranges = GenotypeConfig()
    rng = random.Random(3)

    capacities = [
        draw_genotype(rng, ranges, (0, 0, 255)).digestion_capacity
        for _ in range(50)
    ]

    assert all(40.0 <= value <= 120.0 for value in capacities)
    assert len(set(capacities)) > 1
    assert create_default_phenotype(DEFAULT_GENOTYPE).digestion_capacity == \
        DEFAULT_GENOTYPE.digestion_capacity


def test_snapshots_keep_food_and_feeding_counters(tmp_path):
    """Save/load preserves morsels and lifetime eaten/absorbed totals."""
    config = _make_config()
    original = Container(config)
    bean = original.session.beans[0]
    food = original.session.foods[0]
    bean.x, bean.y = food.x, food.y
    bean.phenotype.current_energy = 50.0
    path = save_snapshot(str(tmp_path / "snap.json"), original, config)

    restored = Container(config)
    restore_snapshot(load_snapshot(path), restored, config)

    assert [f.energy for f in restored.session.foods] == \
        [f.energy for f in original.session.foods]
    assert restored.session.foods == original.session.foods

    session = restored.session
    session.state = GameState.PLAYING
    session.clock.paused = False
    step = 1.0 / config.tick_rate
    _step(session, restored.environment, restored.movement_strategy,
          restored.energy_strategy, step, step, config, max_ticks=1,
          food_strategy=restored.food_strategy)

    eater = next(
        b for b in session.beans if b.phenotype.energy_eaten_total > 0.0
    )
    assert eater.phenotype.energy_absorbed_total > 0.0
    assert eater.phenotype.energy_eaten_total >= \
        eater.phenotype.energy_absorbed_total
