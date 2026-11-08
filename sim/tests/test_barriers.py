"""Tests for density-based, non-deterministic barrier generation."""

from sim.config import BarrierConfig
from sim.domain.world import World
from sim.implementations.barrier import BarrierStrategy


WORLD = World(width=1200.0, height=800.0, cell_size=10.0)


def _spans(barriers, cell_size=10.0):
    return [
        (round(b.width / cell_size), round(b.height / cell_size))
        for b in barriers
    ]


def _covered_cells(barriers, cell_size=10.0):
    return sum(cols * rows for cols, rows in _spans(barriers, cell_size))


def _overlaps(barriers, cell_size=10.0):
    rects = [
        (round(b.x / cell_size), round(b.y / cell_size),
         round(b.width / cell_size), round(b.height / cell_size))
        for b in barriers
    ]
    for index, (col, row, cols, rows) in enumerate(rects):
        for other_col, other_row, other_cols, other_rows in rects[index + 1:]:
            if (
                col < other_col + other_cols
                and other_col < col + cols
                and row < other_row + other_rows
                and other_row < row + rows
            ):
                return True
    return False


def test_density_scales_total_covered_area():
    low = BarrierStrategy(
        BarrierConfig(density=0.005, min_span_cells=3, max_span_cells=8, seed=1)
    ).create_barriers(WORLD)
    high = BarrierStrategy(
        BarrierConfig(density=0.02, min_span_cells=3, max_span_cells=8, seed=1)
    ).create_barriers(WORLD)

    assert _covered_cells(low) >= round(WORLD.cols * WORLD.rows * 0.005)
    assert _covered_cells(high) >= round(WORLD.cols * WORLD.rows * 0.02)
    assert _covered_cells(high) > _covered_cells(low)
    assert not _overlaps(low)
    assert not _overlaps(high)


def test_generated_barriers_respect_min_and_max_spans():
    barriers = BarrierStrategy(
        BarrierConfig(density=0.02, min_span_cells=3, max_span_cells=8, seed=2)
    ).create_barriers(WORLD)

    assert barriers
    for cols, rows in _spans(barriers):
        assert 3 <= cols <= 8
        assert 3 <= rows <= 8


def test_zero_density_generates_nothing():
    barriers = BarrierStrategy(
        BarrierConfig(density=0.0, min_span_cells=3, max_span_cells=8, seed=3)
    ).create_barriers(WORLD)

    assert barriers == []


def test_explicit_seed_is_reproducible_and_default_is_not():
    config = BarrierConfig(density=0.01, min_span_cells=3, max_span_cells=8, seed=4)
    first = BarrierStrategy(config).create_barriers(WORLD)
    second = BarrierStrategy(config).create_barriers(WORLD)

    assert first == second
    assert BarrierConfig().seed is None
