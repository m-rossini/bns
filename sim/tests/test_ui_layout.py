"""Layout tests for the sidebar Controls box.

The config button, the key bindings and the playback-speed slider live in the
same box. These tests pin their vertical bands so the button and the slider can
never overlap again, regardless of sidebar width.
"""

from sim.rendering.arcade_view import (
    _CONTROLS_BOX_H,
    _DAY_BOX_H,
    _END_HINT_GAP,
    _END_LINE_H,
    _END_PANEL_H,
    _ENVIRONMENT_BOX_H,
    _FOOD_BOX_H,
    _GAP,
    _INSPECTOR_BOX_H,
    _KEY_COUNT,
    _KEY_ROW_H,
    _MARGIN,
    _SEASON_BOX_H,
    _TIME_BOX_H,
    SIDEBAR_MIN_HEIGHT,
    controls_geometry,
    end_screen_hint_offset,
    food_geometry,
    inspector_geometry,
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
# Sidebar boxes: Food census and Inspector rows
# ---------------------------------------------------------------------------


def test_sidebar_min_height_fits_every_always_visible_box():
    """The default window is tall enough for the Food box and Controls."""
    expected = (
        2 * _MARGIN
        + _TIME_BOX_H
        + _DAY_BOX_H
        + _SEASON_BOX_H
        + _ENVIRONMENT_BOX_H
        + _INSPECTOR_BOX_H
        + _FOOD_BOX_H
        + 6 * _GAP
        + _CONTROLS_BOX_H
    )
    assert SIDEBAR_MIN_HEIGHT >= expected


def test_inspector_rows_never_overlap():
    """The large temperature and the small readings line stay separate."""
    box_top = 800.0
    cell_y, contents_y, temperature_y, readings_y, condition_y = (
        inspector_geometry(12.0, 276.0, box_top)
    )

    # Rows are ordered top to bottom and fit inside the box.
    assert cell_y > contents_y > temperature_y > readings_y
    assert readings_y >= box_top - _INSPECTOR_BOX_H

    # The 22px temperature text and the 11px readings line never share a band.
    assert temperature_y - readings_y >= 22
    # The condition label aligns with the contents row.
    assert condition_y == contents_y


def test_food_rows_fit_inside_box():
    """The Food census rows stay inside their box."""
    box_top = 800.0
    count_y, energy_y, bar_y, top_up_y = food_geometry(12.0, 276.0, box_top)

    assert count_y > energy_y > bar_y > top_up_y
    assert top_up_y >= box_top - _FOOD_BOX_H
