"""Layout tests for the sidebar Controls box.

The config button, the key bindings and the playback-speed slider live in the
same box. These tests pin their vertical bands so the button and the slider can
never overlap again, regardless of sidebar width.
"""

from sim.rendering.arcade_view import (
    _CENSUS_BOX_H,
    _CONTROLS_BOX_H,
    _DAY_BOX_H,
    _END_HINT_GAP,
    _END_LINE_H,
    _END_PANEL_H,
    _ENVIRONMENT_BOX_H,
    _FOOD_BOX_H,
    _GAP,
    _INSPECTOR_H,
    _INSPECTOR_W,
    _KEY_COUNT,
    _KEY_ROW_H,
    _MARGIN,
    _SEASON_BOX_H,
    _TIME_BOX_H,
    SIDEBAR_MIN_HEIGHT,
    controls_geometry,
    end_screen_hint_offset,
    _config_rows,
    cell_contents,
    food_geometry,
    inspector_popup_geometry,
    inspector_popup_rows,
)

MARGIN = 12.0


def _bands(left=12.0, width=276.0, box_bottom=MARGIN):
    box_top, button, keys_top, slider = controls_geometry(left, width, box_bottom)
    key_bottom = keys_top - (_KEY_COUNT - 1) * _KEY_ROW_H
    return box_top, button, keys_top, key_bottom, slider


def test_controls_box_height_matches_contents():
    """The reserved height is exactly what the three bands need."""
    box_top, button, keys_top, key_bottom, slider = _bands()
    assert box_top == MARGIN + _CONTROLS_BOX_H
    assert button[1] > 0 and slider[1] > 0
    # Everything fits inside the box's vertical extent.
    assert slider[1] >= MARGIN
    assert button[1] + button[3] <= box_top


def test_button_does_not_overlap_key_rows():
    _, button, keys_top, _, _ = _bands()
    button_bottom = button[1]
    assert keys_top < button_bottom
    assert button_bottom - keys_top >= 10  # real gap, not touching


def test_slider_does_not_overlap_key_rows():
    _, _, _, key_bottom, slider = _bands()
    slider_top = slider[1] + slider[3]
    assert slider_top < key_bottom
    assert key_bottom - slider_top >= 20  # room for the speed label


def test_button_and_slider_never_overlap():
    _, button, _, _, slider = _bands()
    button_bottom = button[1]
    slider_top = slider[1] + slider[3]
    assert slider_top < button_bottom


def test_bands_are_stable_across_sidebar_widths():
    for width in (200.0, 276.0, 400.0, 900.0):
        _, button, keys_top, key_bottom, slider = _bands(width=width)
        assert button[1] > keys_top
        assert keys_top > key_bottom
        assert key_bottom > slider[1] + slider[3]
        # Widgets stay inside the sidebar horizontally.
        assert button[0] >= 12.0
        assert button[0] + button[2] <= width - 12.0 + 12.0


def test_config_rows_cover_every_dataclass_field():
    """The config screen is generated, so every field must appear in it."""
    from dataclasses import fields, is_dataclass

    from sim.config import DEFAULT_CONFIG
    from sim.rendering.arcade_view import _config_rows

    for top in fields(DEFAULT_CONFIG):
        value = getattr(DEFAULT_CONFIG, top.name)
        if not is_dataclass(value):
            continue
        rows = _config_rows(value)
        keys = [key for key, _ in rows]
        for nested in fields(value):
            child = getattr(value, nested.name)
            if is_dataclass(child):
                # Nested configs are flattened, so check the key prefix.
                assert any(
                    key.startswith(f"{nested.name}.") for key in keys
                ), (top.name, nested.name)
            else:
                assert nested.name in keys, (top.name, nested.name)


def test_config_rows_render_readable_values():
    from sim.config import BarrierConfig, WorldConfig
    from sim.rendering.arcade_view import _config_rows

    world = dict(_config_rows(WorldConfig()))
    assert world["width"] == "1200"
    assert world["orientation"] == "north_south"
    assert world["wrap_around"] == "false"

    barriers = dict(_config_rows(BarrierConfig()))
    assert barriers["color"] == "(255, 208, 64)"   # yellow
    assert barriers["density"] == "0.01"
    assert barriers["min_span_cells"] == "3"
    assert barriers["max_span_cells"] == "8"


def test_clip_never_exceeds_its_budget():
    from sim.rendering.arcade_view import _clip

    assert _clip("short", 10) == "short"
    clipped = _clip("x" * 80, 10)
    assert len(clipped) == 10
    assert clipped.endswith("…")


def test_config_seasons_are_rendered_per_entry():
    from sim.config import DEFAULT_CONFIG
    from sim.rendering.arcade_view import _config_rows

    rows = _config_rows(DEFAULT_CONFIG.seasons[0])
    keys = [key for key, _ in rows]
    assert "name" in keys
    assert "sun_intensity" in keys


def test_closing_config_window_restores_the_active_window(monkeypatch):
    """Arcade clears its global window on close; the main window must claim it.

    Without this, the first frame after closing the config window raises
    ``RuntimeError: No window is active``.
    """
    import sim.rendering.arcade_view as av

    claimed = []
    monkeypatch.setattr(av.arcade, "set_window", claimed.append)

    class _Session:
        state = av.GameState.CONFIG

    class _View:
        _config_window = object()
        session = _Session()

    view = _View()
    av.ArcadeView._on_config_closed(view)

    assert claimed == [view], "main window was not made active again"
    assert view._config_window is None
    assert view.session.state == av.GameState.PLAYING


# ---------------------------------------------------------------------------
# End-screen restart hint
# ---------------------------------------------------------------------------

# Current stats list on the GAME OVER screen (13 rows + 1 blank spacer).
_END_STAT_ROWS = 14


def _last_stat_offset(panel_h=_END_PANEL_H, rows=_END_STAT_ROWS):
    first = panel_h - 164.0
    return first - ((rows - 1) * _END_LINE_H + 12.0) + _END_LINE_H


def test_restart_hint_sits_below_the_last_stat_row():
    """The SPACE hint must clear the Starved line with a real gap."""
    hint = end_screen_hint_offset(_END_PANEL_H, _END_STAT_ROWS)
    last = _last_stat_offset()

    assert hint < last  # below, not mixed into the stats
    assert last - hint >= _END_LINE_H + 20  # line step plus breathing room
    assert hint >= 20  # still inside the panel, not clipped at the bottom


def test_growing_stat_lists_push_the_hint_down():
    """Adding stat rows moves the hint; it never stays pinned over content."""
    current = end_screen_hint_offset(_END_PANEL_H, _END_STAT_ROWS)
    longer = end_screen_hint_offset(_END_PANEL_H, _END_STAT_ROWS + 2)

    assert longer == current - 2 * _END_LINE_H


# ---------------------------------------------------------------------------
# Sidebar boxes: Food census rows and the always-visible Population box
# ---------------------------------------------------------------------------


def test_sidebar_min_height_fits_every_always_visible_box():
    """The default window fits Time..Food, Population, Controls and weather."""
    expected = (
        2 * _MARGIN
        + _TIME_BOX_H
        + _DAY_BOX_H
        + _SEASON_BOX_H
        + _ENVIRONMENT_BOX_H
        + _FOOD_BOX_H
        + _CENSUS_BOX_H
        + 6 * _GAP
        + _CONTROLS_BOX_H
        + 80.0  # weather census minimum
        + _GAP
    )
    assert SIDEBAR_MIN_HEIGHT >= expected


def test_config_window_lists_new_food_and_sleep_fields():
    """Recently added knobs must show up in the generated config window."""
    from dataclasses import fields, is_dataclass

    from sim.config import DEFAULT_CONFIG

    keys = set()
    for section in fields(DEFAULT_CONFIG):
        value = getattr(DEFAULT_CONFIG, section.name)
        if is_dataclass(value):
            for key, _ in _config_rows(value):
                keys.add(f"{section.name}.{key}")

    for expected in (
        "food.target_fraction",
        "food.target_jitter",
        "food.spoilage_per_tick",
        "food.tick_candidates",
        "movement.rest_speed_fraction",
        "creation.genotype_ranges.dawn_resilience",
    ):
        assert expected in keys, f"{expected} missing from the config window"


def test_inspector_popup_rows_never_overlap():
    """The popup rows are ordered top to bottom and stay inside the panel."""
    left, top, close_rect = inspector_popup_geometry(500.0, 400.0, 1560.0, 1000.0)
    rows = inspector_popup_rows(left, top)

    # Six rows: cell, beans, food, barrier, temperature, readings.
    assert len(rows) == 6
    # Rows are strictly ordered top to bottom and inside the panel.
    assert all(a > b for a, b in zip(rows, rows[1:]))
    assert rows[-1] >= top - _INSPECTOR_H
    # The 22px temperature text and the 11px readings never share a band.
    cell_y, beans_y, food_y, ground_y, temperature_y, readings_y = rows
    assert temperature_y - readings_y >= 22
    # Close button sits inside the panel's top-right corner.
    cx, cy, cw, ch = close_rect
    assert left <= cx and cx + cw <= left + _INSPECTOR_W
    assert top - _INSPECTOR_H <= cy and cy + ch <= top


def test_inspector_popup_clamps_inside_viewport():
    """Crowded anchors still land fully on screen."""
    sw, sh = 1560.0, 1000.0
    for anchor in [(10.0, 10.0), (1550.0, 990.0), (1550.0, 10.0), (780.0, 990.0)]:
        left, top, close_rect = inspector_popup_geometry(*anchor, sw, sh)
        assert 12.0 <= left <= sw - 12.0 - _INSPECTOR_W
        assert _INSPECTOR_H + 12.0 <= top <= sh - 12.0


def test_cell_contents_counts_beans_and_food_by_membership():
    """The popup censuses the whole cell, not just the first match."""
    from sim.domain.beans import Bean
    from sim.domain.food import Food
    from sim.domain.world import World

    world = World(width=200.0, height=200.0, cell_size=10.0)
    beans = [
        Bean(id=1, x=15.0, y=15.0, gender="female", color=(255, 0, 0)),
        Bean(id=2, x=16.0, y=14.0, gender="male", color=(0, 0, 255)),
        Bean(id=3, x=150.0, y=150.0, gender="female", color=(255, 0, 0)),
    ]
    foods = [
        Food(id=1, x=12.0, y=18.0, radius=4.0, energy=50.0, initial_energy=50.0),
        Food(id=2, x=180.0, y=20.0, radius=4.0, energy=30.0, initial_energy=30.0),
    ]
    cell = world.cell_index(15.0, 15.0)

    in_beans, in_foods, barrier = cell_contents(beans, foods, world, cell)

    assert {b.id for b in in_beans} == {1, 2}
    assert [f.id for f in in_foods] == [1]
    assert barrier is None


def test_food_rows_fit_inside_box():
    """The Food census rows stay inside their box."""
    box_top = 800.0
    count_y, energy_y, bar_y, top_up_y = food_geometry(12.0, 276.0, box_top)

    assert count_y > energy_y > bar_y > top_up_y
    assert top_up_y >= box_top - _FOOD_BOX_H
