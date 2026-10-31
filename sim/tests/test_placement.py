"""Tests for bean placement strategies (collision-free)."""

import math
import unittest

from sim.config import (
    DEFAULT_CONFIG,
    BeanPlacementConfig,
    BorderToCenterConfig,
    CenterToBorderConfig,
    ColonyClusterConfig,
    LinearGradientConfig,
    PoissonDiscConfig,
    ResourceGradientConfig,
    SeasonConfig,
    SimulationConfig,
    SymmetricalConfig,
    WorldConfig,
)
from sim.container import Container
from sim.domain.world import World
from sim.implementations.placement import (
    BorderToCenterStrategy,
    CenterToBorderStrategy,
    ColonyClusterStrategy,
    LinearGradientStrategy,
    PoissonDiscStrategy,
    ResourceGradientStrategy,
    SymmetricalStrategy,
)


def _make_world(width=1200.0, height=800.0, cell_size=10.0):
    return World(width=width, height=height, cell_size=cell_size)


def _all_in_bounds(points, width, height):
    return all(0.0 <= x <= width and 0.0 <= y <= height for x, y in points)


def _no_overlaps(points, radius):
    """No two points may be closer than 2*radius."""
    radius_sq = (2.0 * radius) ** 2
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            dx = points[i][0] - points[j][0]
            dy = points[i][1] - points[j][1]
            if dx * dx + dy * dy < radius_sq:
                return False
    return True


class TestPlacementCountAndBounds(unittest.TestCase):
    """Every strategy should return collision-free positions inside bounds."""

    def setUp(self):
        self.world = _make_world()
        self.radius = DEFAULT_CONFIG.bean_placement.bean_radius

    def test_poisson_disc_count_and_bounds(self):
        strat = PoissonDiscStrategy(PoissonDiscConfig(), seed=1)
        points = strat.generate_positions(
            50, 1200.0, 800.0, world=self.world, existing=[], radius=self.radius
        )
        self.assertTrue(_all_in_bounds(points, 1200.0, 800.0))
        self.assertGreater(len(points), 0)
        self.assertLessEqual(len(points), 50)
        self.assertTrue(_no_overlaps(points, self.radius))

    def test_symmetrical_count_and_bounds(self):
        strat = SymmetricalStrategy(SymmetricalConfig(symmetry_axes=4), seed=1)
        points = strat.generate_positions(
            40, 1200.0, 800.0, world=self.world, existing=[], radius=self.radius
        )
        self.assertTrue(_all_in_bounds(points, 1200.0, 800.0))
        self.assertGreater(len(points), 0)
        self.assertTrue(_no_overlaps(points, self.radius))

    def test_colony_cluster_count_and_bounds(self):
        strat = ColonyClusterStrategy(ColonyClusterConfig(), seed=1)
        points = strat.generate_positions(
            60, 1200.0, 800.0, world=self.world, existing=[], radius=self.radius
        )
        self.assertTrue(_all_in_bounds(points, 1200.0, 800.0))
        self.assertGreater(len(points), 0)
        self.assertTrue(_no_overlaps(points, self.radius))

    def test_center_to_border_count_and_bounds(self):
        strat = CenterToBorderStrategy(CenterToBorderConfig(), seed=1)
        points = strat.generate_positions(
            50, 1200.0, 800.0, world=self.world, existing=[], radius=self.radius
        )
        self.assertTrue(_all_in_bounds(points, 1200.0, 800.0))
        self.assertGreater(len(points), 0)
        self.assertLessEqual(len(points), 50)
        self.assertTrue(_no_overlaps(points, self.radius))

    def test_border_to_center_count_and_bounds(self):
        strat = BorderToCenterStrategy(BorderToCenterConfig(), seed=1)
        points = strat.generate_positions(
            50, 1200.0, 800.0, world=self.world, existing=[], radius=self.radius
        )
        self.assertTrue(_all_in_bounds(points, 1200.0, 800.0))
        self.assertGreater(len(points), 0)
        self.assertLessEqual(len(points), 50)
        self.assertTrue(_no_overlaps(points, self.radius))

    def test_linear_gradient_count_and_bounds(self):
        strat = LinearGradientStrategy(LinearGradientConfig(), seed=1)
        points = strat.generate_positions(
            50, 1200.0, 800.0, world=self.world, existing=[], radius=self.radius
        )
        self.assertTrue(_all_in_bounds(points, 1200.0, 800.0))
        self.assertGreater(len(points), 0)
        self.assertLessEqual(len(points), 50)
        self.assertTrue(_no_overlaps(points, self.radius))

    def test_resource_gradient_count_and_bounds(self):
        strat = ResourceGradientStrategy(ResourceGradientConfig(), seed=1)
        points = strat.generate_positions(
            50, 1200.0, 800.0, world=self.world, existing=[], radius=self.radius
        )
        self.assertTrue(_all_in_bounds(points, 1200.0, 800.0))
        self.assertGreater(len(points), 0)
        self.assertTrue(_no_overlaps(points, self.radius))

    def test_zero_population_returns_empty(self):
        strat = PoissonDiscStrategy(PoissonDiscConfig(), seed=1)
        self.assertEqual(
            strat.generate_positions(0, 1200.0, 800.0, world=self.world, radius=self.radius),
            [],
        )


class TestPoissonDiscSpacing(unittest.TestCase):
    """Poisson-disc should enforce a minimum spacing between points."""

    def setUp(self):
        self.world = _make_world()
        self.radius = DEFAULT_CONFIG.bean_placement.bean_radius

    def test_minimum_spacing_respected(self):
        strat = PoissonDiscStrategy(PoissonDiscConfig(base_spacing_scale=1.0), seed=1)
        points = strat.generate_positions(
            30, 1200.0, 800.0, world=self.world, existing=[], radius=self.radius
        )
        self.assertTrue(_all_in_bounds(points, 1200.0, 800.0))
        self.assertGreater(len(points), 0)
        self.assertTrue(_no_overlaps(points, self.radius))


class TestSymmetricalAxes(unittest.TestCase):
    """Symmetrical strategy should respect the axis count."""

    def setUp(self):
        self.world = _make_world()
        self.radius = DEFAULT_CONFIG.bean_placement.bean_radius

    def test_axes_parameter(self):
        for k in (1, 2, 4, 8):
            strat = SymmetricalStrategy(SymmetricalConfig(symmetry_axes=k), seed=1)
            points = strat.generate_positions(
                40, 1200.0, 800.0,
                world=self.world, existing=[], radius=self.radius,
            )
            self.assertTrue(_all_in_bounds(points, 1200.0, 800.0))
            self.assertGreaterEqual(len(points), 1)

    def test_min_axes_is_one(self):
        strat = SymmetricalStrategy(SymmetricalConfig(symmetry_axes=0), seed=1)
        self.assertEqual(strat.symmetry_axes, 1)


class TestDeterminism(unittest.TestCase):
    """Same seed should produce identical results."""

    def setUp(self):
        self.world = _make_world()
        self.radius = DEFAULT_CONFIG.bean_placement.bean_radius

    def test_poisson_disc_deterministic(self):
        a = PoissonDiscStrategy(PoissonDiscConfig(), seed=42).generate_positions(
            25, 1200.0, 800.0,
            world=self.world, existing=[], radius=self.radius,
        )
        b = PoissonDiscStrategy(PoissonDiscConfig(), seed=42).generate_positions(
            25, 1200.0, 800.0,
            world=self.world, existing=[], radius=self.radius,
        )
        self.assertEqual(a, b)

    def test_different_seeds_differ(self):
        a = PoissonDiscStrategy(PoissonDiscConfig(), seed=1).generate_positions(
            25, 1200.0, 800.0,
            world=self.world, existing=[], radius=self.radius,
        )
        b = PoissonDiscStrategy(PoissonDiscConfig(), seed=2).generate_positions(
            25, 1200.0, 800.0,
            world=self.world, existing=[], radius=self.radius,
        )
        self.assertNotEqual(a, b)


class TestCenterToBorderConcentration(unittest.TestCase):
    """Center-to-border should concentrate points near the center."""

    def setUp(self):
        self.world = _make_world()
        self.radius = DEFAULT_CONFIG.bean_placement.bean_radius

    def test_concentrated_near_center(self):
        strat = CenterToBorderStrategy(CenterToBorderConfig(falloff_exponent=3.0), seed=1)
        points = strat.generate_positions(
            200, 1200.0, 800.0,
            world=self.world, existing=[], radius=self.radius,
        )
        cx, cy = 600.0, 400.0
        r_max = min(1200.0, 800.0) / 2.0
        near_center = sum(
            1 for x, y in points if math.hypot(x - cx, y - cy) < r_max * 0.5
        )
        far = sum(
            1 for x, y in points if math.hypot(x - cx, y - cy) > r_max * 0.8
        )
        self.assertGreater(near_center, far)


class TestBorderToCenterConcentration(unittest.TestCase):
    """Border-to-center should keep points away from the center."""

    def setUp(self):
        self.world = _make_world()
        self.radius = DEFAULT_CONFIG.bean_placement.bean_radius

    def test_points_in_outer_ring(self):
        strat = BorderToCenterStrategy(BorderToCenterConfig(), seed=1)
        points = strat.generate_positions(
            200, 1200.0, 800.0,
            world=self.world, existing=[], radius=self.radius,
        )
        cx, cy = 600.0, 400.0
        r_max = min(1200.0, 800.0) / 2.0
        r_min = r_max * (1.0 - 0.4)
        # All points should be at least r_min from center.
        for x, y in points:
            self.assertGreaterEqual(
                math.hypot(x - cx, y - cy), r_min - 1.0,
                f"point ({x},{y}) too close to center",
            )


class TestBarrierCollision(unittest.TestCase):
    """No bean may overlap a barrier."""

    def setUp(self):
        self.world = _make_world()
        self.radius = DEFAULT_CONFIG.bean_placement.bean_radius
        from sim.components import Barrier
        self.world.add_barrier(Barrier(
            id=1, kind="rect", x=550.0, y=350.0,
            width=100.0, height=100.0,
        ))

    def test_no_bean_overlaps_barrier(self):
        strat = PoissonDiscStrategy(PoissonDiscConfig(), seed=1)
        points = strat.generate_positions(
            100, 1200.0, 800.0,
            world=self.world, existing=[], radius=self.radius,
        )
        r = self.radius
        for x, y in points:
            cx = min(max(x, 550.0), 650.0)
            cy = min(max(y, 350.0), 450.0)
            dist_sq = (x - cx) ** 2 + (y - cy) ** 2
            self.assertGreater(dist_sq, r * r, f"bean ({x},{y}) overlaps barrier")


class TestBeanBarrierSeparation(unittest.TestCase):
    """Full container run: no bean overlaps any barrier."""

    def test_container_beans_clear_barriers(self):
        cfg = SimulationConfig(
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
        c = Container(cfg)
        r = c.config.bean_placement.bean_radius
        for bean in c.beans:
            for b in c.world.barriers:
                if b.kind != "rect":
                    continue
                cx = min(max(bean.x, b.x), b.x + b.width)
                cy = min(max(bean.y, b.y), b.y + b.height)
                dist_sq = (bean.x - cx) ** 2 + (bean.y - cy) ** 2
                self.assertGreater(dist_sq, r * r,
                    f"bean {bean.id} ({bean.x},{bean.y}) overlaps barrier {b.id}")


if __name__ == "__main__":
    unittest.main()
