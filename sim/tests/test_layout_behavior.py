"""Behavior tests for the world layout geometry.

The layout maps world units to screen pixels and back, snaps cells to whole
pixels, and centers the drawn world. The view and the hit-test share it, so
these tests pin the round-trips the pointer relies on.
"""

from __future__ import annotations

from sim.domain.world import World
from sim.rendering.layout import WorldLayout, build_layout


def _world() -> World:
    return World(width=200.0, height=100.0, cell_size=10.0)


def test_small_world_grows_to_fill_with_whole_pixel_cells():
    """A small world in a big viewport grows; cells stay integer-snapped."""
    layout = build_layout(1200.0, 800.0, _world())

    assert layout.scale > 1.0
    assert layout.cell_step == round(layout.cell_step)
    assert layout.right == layout.left + 200.0 * layout.scale
    assert layout.top == layout.bottom + 100.0 * layout.scale
    # Centered: equal slack on both sides of the drawn area.
    assert layout.left > 0.0
    assert layout.bottom > 0.0


def test_large_world_scales_down_with_whole_pixel_cells():
    """A world bigger than the viewport shrinks but keeps crisp cells."""
    big = World(width=2000.0, height=1000.0, cell_size=10.0)
    layout = build_layout(400.0, 300.0, big)

    assert layout.scale < 1.0
    assert layout.cell_step == round(layout.cell_step)  # integer-snapped
    assert layout.cell_step >= 1.0


def test_screen_world_round_trip_and_miss():
    """Points convert both ways; outside or degenerate layouts miss cleanly."""
    layout = build_layout(1200.0, 800.0, _world())

    world_point = layout.screen_to_world(layout.left + 50.0, layout.bottom + 25.0)
    assert world_point == (50.0 / layout.scale, 25.0 / layout.scale)
    back = layout.world_to_screen(*world_point)
    assert back == (layout.left + 50.0, layout.bottom + 25.0)

    assert layout.screen_to_world(layout.left - 1.0, layout.bottom) is None
    assert layout.screen_to_world(
        layout.left + 200.0 * layout.scale + 1.0, layout.bottom
    ) is None

    flat = WorldLayout(left=0.0, bottom=0.0, scale=0.0,
                       cell_size=10.0, cols=20, rows=10,
                       world_width=200.0, world_height=100.0)
    assert flat.screen_to_world(5.0, 5.0) is None


def test_cell_math_matches_the_world_grid():
    """Cell index clamps, centers land on half-steps, rects tile exactly."""
    layout = build_layout(1200.0, 800.0, _world())
    step = layout.cell_step

    assert layout.cell_index(5.0, 5.0) == (0, 0)
    assert layout.cell_index(-50.0, 999.0) == (0, 9)
    assert layout.cell_center(0, 0) == (5.0, 5.0)
    assert layout.cell_bounds(1, 2) == (10.0, 20.0, 10.0, 10.0)

    first = layout.cell_screen_rect(0, 0)
    second = layout.cell_screen_rect(1, 0)
    assert first == (layout.left, layout.bottom, step, step)
    assert second[0] == first[0] + step  # neighbours tile without gaps
