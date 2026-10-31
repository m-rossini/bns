"""Tests for the spawn controller and area-based population calculus."""

import unittest

from sim.config import (
    BEAN_DENSITY_COEFFICIENTS,
    BeanPlacementConfig,
    SimulationConfig,
    WorldConfig,
)
from sim.container import Container


def _make_config(**overrides):
    base = SimulationConfig(
        world=WorldConfig(width=1200.0, height=800.0, cell_size=10.0),
        bean_placement=BeanPlacementConfig(
            strategy_name="poisson_disc",
            density_tier="average",
            variance=0.0,
            seed=42,
            gender_ratios={"male": 50.0, "female": 50.0},
            gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
        ),
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


class TestPopulationCalculus(unittest.TestCase):
    def test_population_scales_with_area(self):
        small = Container(
            _make_config(world=WorldConfig(width=200.0, height=200.0))
        )
        large = Container(
            _make_config(world=WorldConfig(width=1200.0, height=800.0))
        )
        self.assertLess(len(small.beans), len(large.beans))

    def test_density_tier_changes_population(self):
        sparse = Container(
            _make_config(
                bean_placement=BeanPlacementConfig(
                    strategy_name="poisson_disc",
                    density_tier="sparse",
                    variance=0.0,
                    seed=42,
                    gender_ratios={"male": 50.0, "female": 50.0},
                    gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
                )
            )
        )
        heavy = Container(
            _make_config(
                bean_placement=BeanPlacementConfig(
                    strategy_name="poisson_disc",
                    density_tier="heavy",
                    variance=0.0,
                    seed=42,
                    gender_ratios={"male": 50.0, "female": 50.0},
                    gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
                )
            )
        )
        self.assertLess(len(sparse.beans), len(heavy.beans))

    def test_variance_changes_population_across_seeds(self):
        counts = []
        for seed in (1, 2, 3, 4, 5):
            cfg = _make_config(
                bean_placement=BeanPlacementConfig(
                    strategy_name="poisson_disc",
                    density_tier="average",
                    variance=0.20,
                    seed=seed,
                    gender_ratios={"male": 50.0, "female": 50.0},
                    gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
                )
            )
            counts.append(len(Container(cfg).beans))
        # With 20% variance, counts should differ across seeds (not all identical).
        self.assertGreater(len(set(counts)), 1)

    def test_all_beans_have_gender_and_color_and_are_in_bounds(self):
        c = Container(_make_config())
        for bean in c.beans:
            self.assertIn(bean.gender, ("male", "female"))
            self.assertIn(bean.color, ((0, 0, 255), (255, 0, 0)))
            self.assertGreaterEqual(bean.x, 0.0)
            self.assertLessEqual(bean.x, 1200.0)
            self.assertGreaterEqual(bean.y, 0.0)
            self.assertLessEqual(bean.y, 800.0)


class TestConfigValidation(unittest.TestCase):
    def test_invalid_density_tier_rejected(self):
        with self.assertRaises(ValueError):
            BeanPlacementConfig(
                strategy_name="poisson_disc",
                density_tier="not_a_tier",
                variance=0.1,
                seed=1,
                gender_ratios={"male": 50.0, "female": 50.0},
                gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
            )

    def test_variance_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            BeanPlacementConfig(
                strategy_name="poisson_disc",
                density_tier="average",
                variance=1.5,
                seed=1,
                gender_ratios={"male": 50.0, "female": 50.0},
                gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
            )
        with self.assertRaises(ValueError):
            BeanPlacementConfig(
                strategy_name="poisson_disc",
                density_tier="average",
                variance=-0.1,
                seed=1,
                gender_ratios={"male": 50.0, "female": 50.0},
                gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
            )

    def test_gender_ratios_not_summing_to_100_rejected(self):
        with self.assertRaises(ValueError):
            BeanPlacementConfig(
                strategy_name="poisson_disc",
                density_tier="average",
                variance=0.1,
                seed=1,
                gender_ratios={"male": 50.0, "female": 40.0},
                gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
            )

    def test_invalid_strategy_name_rejected_by_container(self):
        cfg = _make_config(
            bean_placement=BeanPlacementConfig(
                strategy_name="nonexistent_strategy",
                density_tier="average",
                variance=0.1,
                seed=1,
                gender_ratios={"male": 50.0, "female": 50.0},
                gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
            )
        )
        with self.assertRaises(ValueError):
            Container(cfg)


if __name__ == "__main__":
    unittest.main()
