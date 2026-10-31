"""Tests for the spawn controller and area-based population calculus."""

import unittest

from sim.config import (
    BEAN_DENSITY_COEFFICIENTS,
    BeanPlacementConfig,
    ColonyClusterConfig,
    PoissonDiscConfig,
    SeasonConfig,
    SimulationConfig,
    WorldConfig,
)
from sim.container import Container


def _make_config(**overrides):
    base = SimulationConfig(
        world=WorldConfig(width=1200.0, height=800.0, cell_size=10.0),
        seasons=[
            SeasonConfig(
                name="Spring", ground_color=(96, 170, 88),
                base_temperature=14.0, temperature_swing=7.0,
                humidity=0.55, pressure_hpa=1012.0,
                sun_intensity=0.95, daylight_fraction=0.50,
                ground_meaning="growing season",
                weather_weights={"clear": 30, "cloudy": 30, "rain": 30, "storm": 10, "snow": 0},
            ),
        ],
        bean_placement=BeanPlacementConfig(
            strategy_name="poisson_disc",
            density_tier="average",
            variance=0.0,
            seed=42,
            gender_ratios={"male": 50.0, "female": 50.0},
            gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
            bean_radius=5.0,
            poisson_disc=PoissonDiscConfig(),
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
                    bean_radius=5.0,
                    poisson_disc=PoissonDiscConfig(),
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
                    bean_radius=5.0,
                    poisson_disc=PoissonDiscConfig(),
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
                    bean_radius=5.0,
                    poisson_disc=PoissonDiscConfig(),
                )
            )
            counts.append(len(Container(cfg).beans))
        # With 20% variance, counts should differ across seeds (not all identical).
        self.assertGreater(len(set(counts)), 1)

    def test_expected_population_matches_formula(self):
        # variance=0 => N ≈ Round(A * rho). Collision-free placement may
        # produce fewer due to minimum spacing constraints.
        area = 1200.0 * 800.0  # 960000
        rho = BEAN_DENSITY_COEFFICIENTS["average"]  # 0.0020
        expected = round(area * rho)  # 1920
        c = Container(_make_config())
        # Expect a substantial fraction of the theoretical max.
        self.assertGreater(len(c.beans), expected * 0.5)
        self.assertLessEqual(len(c.beans), expected)

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
                bean_radius=5.0,
                poisson_disc=PoissonDiscConfig(),
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
                bean_radius=5.0,
                poisson_disc=PoissonDiscConfig(),
            )
        with self.assertRaises(ValueError):
            BeanPlacementConfig(
                strategy_name="poisson_disc",
                density_tier="average",
                variance=-0.1,
                seed=1,
                gender_ratios={"male": 50.0, "female": 50.0},
                gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
                bean_radius=5.0,
                poisson_disc=PoissonDiscConfig(),
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
                bean_radius=5.0,
                poisson_disc=PoissonDiscConfig(),
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
                bean_radius=5.0,
                poisson_disc=PoissonDiscConfig(),
            )
        )
        with self.assertRaises(ValueError):
            Container(cfg)


if __name__ == "__main__":
    unittest.main()
