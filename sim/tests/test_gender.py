"""Tests for the gender controller."""

import unittest

from sim.config import BeanPlacementConfig
from sim.implementations.gender import GenderController


def _make_config(ratios=None, colors=None, seed=1337):
    return BeanPlacementConfig(
        strategy_name="poisson_disc",
        density_tier="average",
        variance=0.1,
        seed=seed,
        gender_ratios=ratios or {"male": 50.0, "female": 50.0},
        gender_colors=colors or {"male": (0, 0, 255), "female": (255, 0, 0)},
    )


class TestGenderControllerConstruction(unittest.TestCase):
    def test_default_ratios_sum_to_100(self):
        cfg = _make_config()
        ctrl = GenderController(cfg)
        self.assertEqual(ctrl.gender_names, ("male", "female"))

    def test_ratios_must_sum_to_100(self):
        with self.assertRaises(ValueError):
            BeanPlacementConfig(
                strategy_name="poisson_disc",
                density_tier="average",
                variance=0.1,
                seed=1,
                gender_ratios={"male": 50.0, "female": 40.0},
                gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
            )

    def test_missing_color_rejected(self):
        # GenderController (not BeanPlacementConfig) validates that every
        # gender in ratios has a color.
        cfg = BeanPlacementConfig(
            strategy_name="poisson_disc",
            density_tier="average",
            variance=0.1,
            seed=1,
            gender_ratios={"male": 50.0, "female": 50.0},
            gender_colors={"male": (0, 0, 255)},
        )
        with self.assertRaises(ValueError):
            GenderController(cfg)

    def test_colors_match_config(self):
        ctrl = GenderController(_make_config())
        self.assertEqual(ctrl.colors["male"], (0, 0, 255))
        self.assertEqual(ctrl.colors["female"], (255, 0, 0))


class TestGenderAssignment(unittest.TestCase):
    def test_returns_one_assignment_per_position(self):
        ctrl = GenderController(_make_config())
        positions = [(10.0, 10.0), (20.0, 20.0), (30.0, 30.0)]
        result = ctrl.assign_attributes(positions)
        self.assertEqual(len(result), 3)
        for pos, gender, color in result:
            self.assertIn(pos, positions)
            self.assertIn(gender, ("male", "female"))
            self.assertEqual(len(color), 3)

    def test_empty_positions(self):
        ctrl = GenderController(_make_config())
        self.assertEqual(ctrl.assign_attributes([]), [])

    def test_50_50_split_is_balanced(self):
        ctrl = GenderController(_make_config())
        positions = [(float(i), float(i)) for i in range(100)]
        result = ctrl.assign_attributes(positions)
        males = sum(1 for _, g, _ in result if g == "male")
        females = sum(1 for _, g, _ in result if g == "female")
        self.assertEqual(males + females, 100)
        self.assertAlmostEqual(males, 50, delta=1)
        self.assertAlmostEqual(females, 50, delta=1)

    def test_uneven_ratios_respected(self):
        cfg = BeanPlacementConfig(
            strategy_name="poisson_disc",
            density_tier="average",
            variance=0.1,
            seed=1,
            gender_ratios={"male": 75.0, "female": 25.0},
            gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
        )
        ctrl = GenderController(cfg)
        positions = [(float(i), float(i)) for i in range(100)]
        result = ctrl.assign_attributes(positions)
        males = sum(1 for _, g, _ in result if g == "male")
        females = sum(1 for _, g, _ in result if g == "female")
        self.assertAlmostEqual(males, 75, delta=2)
        self.assertAlmostEqual(females, 25, delta=2)

    def test_assignment_is_shuffled_not_sequential(self):
        cfg = BeanPlacementConfig(
            strategy_name="poisson_disc",
            density_tier="average",
            variance=0.1,
            seed=42,
            gender_ratios={"male": 50.0, "female": 50.0},
            gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
        )
        ctrl = GenderController(cfg)
        positions = [(float(i), float(i)) for i in range(40)]
        result = ctrl.assign_attributes(positions)
        genders = [g for _, g, _ in result]
        adjacent_same = sum(
            1 for i in range(len(genders) - 1) if genders[i] == genders[i + 1]
        )
        # With 40 items and 50/50 split, shuffled should have far fewer
        # adjacent same-gender pairs than sequential (which would have ~39).
        self.assertLess(adjacent_same, 20)


class TestGenderColorMapping(unittest.TestCase):
    def test_male_is_blue_female_is_red(self):
        cfg = _make_config()
        ctrl = GenderController(cfg)
        positions = [(1.0, 1.0), (2.0, 2.0)]
        result = ctrl.assign_attributes(positions)
        by_gender = {g: c for _, g, c in result}
        self.assertEqual(by_gender.get("male"), (0, 0, 255))
        self.assertEqual(by_gender.get("female"), (255, 0, 0))


if __name__ == "__main__":
    unittest.main()
