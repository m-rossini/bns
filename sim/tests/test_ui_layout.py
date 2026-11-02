"""Layout tests for the sidebar Controls box.

The config button, the key bindings and the playback-speed slider live in the
same box. These tests pin their vertical bands so the button and the slider can
never overlap again, regardless of sidebar width.
"""

from sim.rendering.arcade_view import (
    _CONTROLS_BOX_H,
    _KEY_COUNT,
    _KEY_ROW_H,
    controls_geometry,
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
