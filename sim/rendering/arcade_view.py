"""Physical screen representation using Arcade.

Reads a read-only snapshot of GameSession and draws state-specific screens.
Never mutates domain state.

Layout
------
* Left: a full-height sidebar with stacked information boxes (time, day,
  season, environment, inspector, weather field, controls).
* Right: the world, using the full height of the window.
* All colours come from the environment strategies (season palette, sky
  palette); the view only owns neutral UI chrome.

Rendering contract
------------------
* The world grid is `world.cell_size` world units. The view applies one
  uniform world -> screen scale, so cells are never assumed to be a pixel
  size and the grid always follows the configured cell size.
* Text is drawn with cached `arcade.Text` objects (never `arcade.draw_text`,
  which is extremely slow and emits a PerformanceWarning).
* Screen coordinates are taken from the active viewport and mouse events are
  scaled from window coordinates, so clicks line up with the highlighted cell
  on HiDPI/scaled displays too.
"""

import logging
import math
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import arcade

from sim.components import GameSession, GameState
from sim.config import SimulationConfig
from sim.domain.food import seasonal_abundance as _seasonal_abundance
from sim.domain.food import total_energy as _food_total_energy
from sim.domain.visuals import SeasonPalette, SkyPalette
from sim.domain.world import World
from sim.rendering.layout import WorldLayout, build_layout

logger = logging.getLogger("bean.ui")

# --- UI chrome (not environmental colours) ---------------------------------
_TEXT = (238, 240, 245)
_MUTED = (168, 176, 190)
_DIM = (120, 128, 142)
_PANEL_BG = (8, 12, 20, 210)
_PANEL_BORDER = (255, 255, 255, 42)
_ACCENT = (120, 230, 150)
_INSPECT = (255, 120, 110)
_HOVER = (255, 255, 255, 110)
_TRACK = (38, 44, 56, 230)
_SUN = (255, 205, 110)
_MOON = (225, 230, 248)

# End-screen panel geometry. Stats start this far below the panel top and
# step down one line each; the restart hint is always placed relative to the
# last stat row so growing stat lists can never collide with it.
_END_PANEL_H = 496.0
_END_STATS_TOP_MARGIN = 164.0
_END_LINE_H = 20.0
_END_HINT_GAP = 50.0


def end_screen_hint_offset(panel_h: float, stat_rows: int,
                           blank_rows: int = 1) -> float:
    """Offset of the restart hint from the panel bottom.

    ``stat_rows`` counts every entry in the stats list (including blanks,
    which step down 0.6 of a line). The hint lands below the last drawn row
    with room for the line step plus a fixed gap.
    """
    first_row = panel_h - _END_STATS_TOP_MARGIN
    drop = ((stat_rows - blank_rows) * _END_LINE_H
            + blank_rows * _END_LINE_H * 0.6)
    last_row = first_row - drop + _END_LINE_H
    return last_row - _END_HINT_GAP
_WEATHER_LABEL = {
    "clear": (255, 226, 140),
    "cloudy": (200, 205, 215),
    "rain": (165, 205, 255),
    "storm": (185, 165, 250),
    "snow": (235, 245, 255),
}

# Per-cell tint applied to the ground: (colour, alpha 0..1)
_WEATHER_TINT = {
    "clear": None,
    "cloudy": ((92, 98, 110), 0.20),
    "rain": ((70, 96, 132), 0.30),
    "storm": ((46, 50, 70), 0.42),
    "snow": ((236, 244, 252), 0.38),
}
_WEATHER_DIM = {"clear": 1.0, "cloudy": 0.82, "rain": 0.68, "storm": 0.5, "snow": 0.85}

#: Weather tints and precipitation are sampled in blocks of this many cells.
#: Weather patches span many cells, so drawing one block per sample looks the
#: same while removing most of the per-cell `weather_at` calls and draw calls.
_WEATHER_BLOCK_CELLS = 3

#: Number of decorative ground specks, drawn from one cached shape list.
_DETAIL_COUNT = 150

_MARGIN = 12.0
_GAP = 8.0
_SIDEBAR_MIN = 300.0

# Heights of the fixed sidebar boxes. They are named constants so the layout
# code and the minimum-window-height calculation cannot drift apart.
_TIME_BOX_H = 92.0
_DAY_BOX_H = 96.0
_SEASON_BOX_H = 84.0
_ENVIRONMENT_BOX_H = 128.0
_INSPECTOR_BOX_H = 128.0
_FOOD_BOX_H = 100.0

# Height of the bottom-anchored "Controls" box: title, config button, five
# key rows, then the playback-speed slider in its own band. The sidebar
# reserves exactly this much so nothing can ever overlap it.
_CONTROLS_BOX_H = (
    32        # title band
    + 24 + 14  # config button + gap
    + 5 * 20   # key rows
    + 12       # gap before slider
    + 34       # slider label + track
)

#: Smallest window height that fits every always-visible sidebar box plus the
#: bottom-anchored Controls box. ``main`` uses this for the default window.
SIDEBAR_MIN_HEIGHT = (
    2 * _MARGIN
    + _TIME_BOX_H
    + _DAY_BOX_H
    + _SEASON_BOX_H
    + _ENVIRONMENT_BOX_H
    + _INSPECTOR_BOX_H
    + _FOOD_BOX_H
    + 6 * _GAP
    + _CONTROLS_BOX_H
    + 4.0  # breathing room so the last box never touches the Controls gap
)

_KEY_ROW_H = 20.0
_KEY_COUNT = 5
_BUTTON_H = 24.0
_SLIDER_TRACK_H = 6.0
_SLIDER_THUMB_W = 10.0


def _format_config_value(value) -> str:
    """One-line, readable rendering of a config value."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {_format_config_value(v)}" for k, v in value.items()) + "}"
    if isinstance(value, (list, tuple)):
        inner = ", ".join(_format_config_value(v) for v in value)
        return f"[{inner}]" if isinstance(value, list) else f"({inner})"
    if value is None:
        return "none"
    return str(value)


def _clip(text: str, limit: int) -> str:
    """Trim a rendered value so it cannot bleed into the next column."""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _config_rows(obj) -> List[Tuple[str, str]]:
    """Flatten a config dataclass into ``(key, rendered_value)`` rows."""
    rows: List[Tuple[str, str]] = []
    for field_info in fields(obj):
        value = getattr(obj, field_info.name)
        if is_dataclass(value):
            for key, text in _config_rows(value):
                rows.append((f"{field_info.name}.{key}", text))
        else:
            rows.append((field_info.name, _format_config_value(value)))
    return rows


def inspector_geometry(left: float, width: float, box_top: float):
    """Layout of the Inspector box rows.

    Returns ``(cell_y, contents_y, temperature_y, readings_y, condition_y)``.
    The large temperature baseline and the small RH/pressure/light baseline
    are distinct so the two lines can never overlap, and every row stays
    inside the box (``_INSPECTOR_BOX_H``).
    """
    return (
        box_top - 38.0,    # cell coordinates
        box_top - 62.0,    # contents (BEAN/BARRIER/EMPTY)
        box_top - 90.0,    # large temperature
        box_top - 114.0,   # RH / pressure / light
        box_top - 62.0,    # condition, right-aligned
    )


def food_geometry(left: float, width: float, box_top: float):
    """Layout of the Food box rows.

    Returns ``(count_y, energy_y, bar_y, top_up_y)``.
    """
    return (
        box_top - 38.0,    # morsel count / average energy
        box_top - 58.0,    # energy / target
        box_top - 72.0,    # energy bar
        box_top - 88.0,    # top-up interval
    )


def controls_geometry(left: float, width: float, box_bottom: float):
    """Layout of the bottom-anchored Controls box.

    Returns ``(box_top, button_rect, keys_top, slider_rect)``. The bands are
    computed from one place so the drawing code and any hit-testing (or test)
    cannot drift apart: the button never touches the keys, and the keys never
    touch the slider.
    """
    box_top = box_bottom + _CONTROLS_BOX_H
    button_rect = (
        left + 12.0,
        box_top - 32.0 - _BUTTON_H,
        width - 24.0,
        _BUTTON_H,
    )
    keys_top = button_rect[1] - 16.0
    slider_rect = (
        left + 12.0,
        box_bottom + 12.0,
        width - 24.0,
        _SLIDER_TRACK_H,
    )
    return box_top, button_rect, keys_top, slider_rect
_SIDEBAR_MAX = 360.0
_TEXT_CACHE_LIMIT = 1024

# Playback-speed slider colours (UI chrome).
_SLIDER_TRACK = (38, 44, 56, 230)
_SLIDER_TRACK_FILLED = (120, 230, 150, 230)
_SLIDER_THUMB = (238, 240, 245)
_SLIDER_THUMB_EDGE = (120, 230, 150)

# Playback-speed slider range (matches `TimeConfig` defaults). The slider only
# changes perceived speed, never `tick_rate` or sim-time progression.
_TIME_SCALE_MIN = 0.1
_TIME_SCALE_MAX = 4.0


def _mix(a, b, t: float):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _shade(color, factor: float):
    return tuple(max(0, min(255, int(round(c * factor)))) for c in color[:3])


def _point_in_rect(x: float, y: float, rect: Tuple[float, float, float, float]) -> bool:
    lx, ly, lw, lh = rect
    return lx <= x <= lx + lw and ly <= y <= ly + lh


class _TextCache:
    """Reuse `arcade.Text` objects instead of calling `arcade.draw_text`.

    `draw_text` re-lays out and re-uploads a texture on every call, which is
    both slow and noisy (Arcade raises a PerformanceWarning). Text objects are
    cached by content + style and only repositioned before drawing.
    """

    def __init__(self) -> None:
        self._items: Dict[tuple, "arcade.Text"] = {}

    def draw(
        self,
        text: str,
        x: float,
        y: float,
        color,
        font_size: float = 12,
        anchor_x: str = "left",
        anchor_y: str = "baseline",
        bold: bool = False,
        width: Optional[int] = None,
        align: str = "left",
        multiline: bool = False,
    ) -> "arcade.Text":
        text = str(text)
        color = tuple(color)
        key = (
            text,
            color,
            float(font_size),
            anchor_x,
            anchor_y,
            bool(bold),
            width,
            align,
            multiline,
        )
        item = self._items.get(key)
        if item is None:
            if len(self._items) >= _TEXT_CACHE_LIMIT:
                self._items.clear()
            item = arcade.Text(
                text,
                x,
                y,
                color=color,
                font_size=font_size,
                anchor_x=anchor_x,
                anchor_y=anchor_y,
                bold=bold,
                width=width,
                align=align,
                multiline=multiline,
            )
            self._items[key] = item
        else:
            item.x = x
            item.y = y
        item.draw()
        return item


class ArcadeView(arcade.Window):
    def __init__(
        self,
        session: GameSession,
        width: int = 1200,
        height: int = 800,
        title: str = "Bean World",
        tick_rate: float = 30.0,
        sim_config: SimulationConfig | None = None,
    ):
        super().__init__(width, height, title, resizable=True)
        self.session = session
        self.sim_config = sim_config
        self._tick_rate = max(tick_rate, 0.001)
        self._input = None
        self._text = _TextCache()

        world = session.world
        # Cells are the authoritative grid: use cols*cell_size so the drawn
        # world is exactly an integer number of cells even if width/height are
        # not exact multiples of cell_size.
        if world is not None:
            self._cell_size = world.cell_size
            self._cols = world.cols
            self._rows = world.rows
            self._world_width = world.cols * world.cell_size
            self._world_height = world.rows * world.cell_size
        else:
            self._cell_size = 50.0
            self._cols = 1
            self._rows = 1
            self._world_width = 1200.0
            self._world_height = 800.0

        self._layout: Optional[WorldLayout] = None
        self._layout_size: Optional[Tuple[int, int]] = None

        self._hover_cell: Optional[Tuple[int, int]] = None
        self._selected_cell: Optional[Tuple[int, int]] = None
        self._slider_rect: Optional[Tuple[float, float, float, float]] = None
        self._slider_dragging = False
        self._config_rect: Optional[Tuple[float, float, float, float]] = None
        self._config_window: Optional["ConfigWindow"] = None
        #: Cached, block-sampled weather conditions. The weather field only
        #: changes once per `WeatherConfig.change_interval` ticks, so querying
        #: every cell every frame is wasted work.
        self._weather_blocks_key: Optional[tuple] = None
        self._weather_blocks_cache: List[Tuple[int, int, str]] = []
        #: Shape list for the weather tints, rebuilt only when the field,
        #: ambient light bucket or layout changes.
        self._weather_shapes = None
        self._weather_shapes_key: Optional[tuple] = None
        #: Cached decorative ground specks (static positions and colours).
        self._detail_shapes = None
        self._detail_shapes_key: Optional[tuple] = None
        self._last_mouse_x: float = 0.0
        self._last_mouse_y: float = 0.0
        self._census_cache: Optional[tuple] = None
        self._census_counts: Dict[str, int] = {}

        self._recompute_layout()

    # ------------------------------------------------------------------
    # Input wiring
    # ------------------------------------------------------------------
    def set_input_handler(self, handler) -> None:
        self._input = handler

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if self._input is not None:
            self._input.handle_keypress(symbol)

    # ------------------------------------------------------------------
    # Screen / mouse mapping
    # ------------------------------------------------------------------
    def _viewport_size(self) -> Tuple[float, float]:
        """Size the projection actually uses (framebuffer pixels on HiDPI)."""
        vp = self.viewport
        if vp[2] > 0 and vp[3] > 0:
            return float(vp[2]), float(vp[3])
        w, h = self.get_size()
        return max(1.0, float(w)), max(1.0, float(h))

    def _mouse_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        """Window (logical) mouse coordinates.

        Hit-testing and drawing share one logical-coordinate layout
        (`WorldLayout`), so no viewport/scale conversion is applied here.
        """
        return float(x), float(y)

    def _ensure_layout(self) -> None:
        size = self._viewport_size()
        if size != self._layout_size or self._layout is None:
            self._layout_size = size
            sidebar = self._sidebar_width()
            self._layout = build_layout(
                size[0], size[1],
                self.session.world,
                sidebar_width=sidebar,
            )

    # ------------------------------------------------------------------
    # Environment accessors
    # ------------------------------------------------------------------
    def _env(self):
        return self.session.environment

    def _palette(self) -> SeasonPalette:
        env = self._env()
        if env is None:
            return SeasonPalette(
                name="Static", ground=(110, 150, 110), details=((140, 170, 140),),
                base_temperature=14.0, temperature_swing=7.0,
                humidity=0.5, pressure_hpa=1013.0,
            )
        return env.palette

    def _sky(self) -> SkyPalette:
        env = self._env()
        if env is None or env.daynight_strategy is None:
            return SkyPalette(
                night=(10, 14, 32), day=(122, 182, 228), twilight=(232, 138, 84),
                overcast=(92, 98, 110), sun=(255, 228, 130),
                moon=(222, 228, 245), star=(235, 240, 255),
            )
        return env.daynight_strategy.sky_palette()

    def _celestial(self, session: GameSession):
        env = session.environment
        if env is None or env.daynight_strategy is None:
            return None
        return env.daynight_strategy.celestial(env.calendar)

    def _cell_center(self, cell: Optional[Tuple[int, int]]):
        world = self.session.world
        if cell is None or world is None:
            return None
        return world.cell_center(*cell)

    def _reading(self, session: GameSession):
        """World position used for the 'environment' box."""
        selected = self._cell_center(self._selected_cell)
        if selected is not None:
            return selected, "SELECTED"
        hover = self._cell_center(self._hover_cell)
        if hover is not None:
            return hover, "CURSOR"
        return (self._world_width / 2.0, self._world_height / 2.0), "CENTER"

    def _light(self, session: GameSession) -> float:
        env = session.environment
        return env.light_level if env is not None else 0.7

    def _season(self, session: GameSession) -> str:
        env = session.environment
        return env.season if env is not None else "Static"

    def _phase(self, session: GameSession) -> str:
        env = session.environment
        return env.phase if env is not None else "day"

    def _ambient(self, session: GameSession) -> float:
        light = self._light(session)
        weather = self._env().weather if self._env() is not None else "clear"
        return max(0.0, min(1.0, light * _WEATHER_DIM.get(weather, 1.0)))

    def _sky_color(self, session: GameSession):
        palette = self._sky()
        light = self._light(session)
        phase = self._phase(session)
        weather = self._env().weather if self._env() is not None else "clear"

        sky = _mix(palette.night, palette.day, light)
        if phase in ("dawn", "dusk"):
            strength = max(0.0, 1.0 - abs(light - 0.28) / 0.28)
            sky = _mix(sky, palette.twilight, 0.55 * strength)
        if weather == "cloudy":
            sky = _mix(sky, palette.overcast, 0.35)
        elif weather == "rain":
            sky = _mix(sky, palette.overcast, 0.55)
        elif weather == "storm":
            sky = _mix(sky, _shade(palette.overcast, 0.6), 0.7)
        elif weather == "snow":
            sky = _mix(sky, (196, 204, 216), 0.5)
        return sky

    # ------------------------------------------------------------------
    # Screens
    # ------------------------------------------------------------------
    def draw_start_screen(self) -> None:
        self.clear(self._sky_color(self.session))
        self._draw_backdrop(self.session)
        self._draw_title_panel("BEAN WORLD", "Press SPACE to start")

    def draw_playing(self, session: GameSession) -> None:
        self.clear(_shade(self._sky_color(session), 0.55))
        self._draw_world(session)
        self._draw_sidebar(session)

    def draw_paused(self, session: GameSession) -> None:
        sw, sh = self._viewport_size()
        self.draw_playing(session)
        arcade.draw_lbwh_rectangle_filled(0, 0, sw, sh, (0, 0, 0, 150))
        self._text.draw(
            "PAUSED", sw / 2, sh / 2 + 18, _TEXT,
            font_size=44, anchor_x="center", anchor_y="center", bold=True,
        )
        self._text.draw(
            "P to resume   ·   Esc or Q to quit", sw / 2, sh / 2 - 28,
            _MUTED, font_size=15, anchor_x="center", anchor_y="center",
        )

    def draw_end_screen(self, session: GameSession) -> None:
        self.clear(_shade(self._sky_color(session), 0.35))
        self._draw_backdrop(session)
        sw, sh = self._viewport_size()
        panel_w = min(620, sw - 60)
        panel_h = _END_PANEL_H
        left = (sw - panel_w) / 2
        bottom = (sh - panel_h) / 2
        self._panel(left, bottom, panel_w, panel_h)

        cx = sw / 2
        self._text.draw(
            "GAME OVER", cx, bottom + panel_h - 70, (240, 96, 96),
            font_size=44, anchor_x="center", anchor_y="center", bold=True,
        )
        self._text.draw(
            f"Reason: {session.end_reason or 'ended'}", cx, bottom + panel_h - 120,
            _TEXT, font_size=19, anchor_x="center", anchor_y="center",
        )

        # --- Statistics wind-down ---------------------------------------
        env = session.environment
        calendar = env.calendar if env is not None else None
        weather = env.weather if env is not None else "clear"
        season = calendar.season if calendar is not None else "Static"
        year = calendar.year if calendar is not None else 1
        day = calendar.day if calendar is not None else 1
        clock = calendar.clock if calendar is not None else "00:00"
        tick = session.clock.tick

        beans = getattr(session, "beans", None) or []
        corpses = getattr(session, "corpses", None) or []
        foods = getattr(session, "foods", None) or []
        food_energy = _food_total_energy(foods)
        initial_female = getattr(session, "initial_female", 0)
        initial_male = getattr(session, "initial_male", 0)
        alive_female = sum(1 for b in beans if b.gender == "female")
        alive_male = len(beans) - alive_female
        dead_female = max(0, initial_female - alive_female)
        dead_male = max(0, initial_male - alive_male)
        total_initial = initial_female + initial_male
        total_alive = alive_female + alive_male
        total_dead = dead_female + dead_male

        stats = [
            (f"Ticks played: {tick}", _TEXT),
            (f"Day {day}  ·  {clock}", _TEXT),
            (f"Season: {season}  ·  Year: {year}", _TEXT),
            (f"Weather: {weather}", _WEATHER_LABEL.get(weather, _TEXT)),
            ("", None),
            ("BEANS", _ACCENT),
            (f"  Initial: {total_initial:>3}  (F:{initial_female:>2} M:{initial_male:>2})", _TEXT),
            (f"  Alive:   {total_alive:>3}  (F:{alive_female:>2} M:{alive_male:>2})", _TEXT),
            (f"  Dead:    {total_dead:>3}  (F:{dead_female:>2} M:{dead_male:>2})", _TEXT),
            (f"  Corpses: {len(corpses):>3}", _TEXT),
            (f"  Foods:   {len(foods):>3}", _TEXT),
            (f"  Food E:  {food_energy:>6.0f}", _TEXT),
            (f"  Old age: {getattr(session, 'deaths_old_age', 0):>3}", _TEXT),
            (f"  Starved: {getattr(session, 'deaths_starvation', 0):>3}", _TEXT),
        ]

        y = bottom + panel_h - _END_STATS_TOP_MARGIN
        line_h = _END_LINE_H
        for text, color in stats:
            if text == "":
                y -= line_h * 0.6
                continue
            self._text.draw(
                text, cx, y, color, font_size=14,
                anchor_x="center", anchor_y="center",
            )
            y -= line_h

        # Hint follows the last stat row so longer stat lists can never
        # collide with it.
        self._text.draw(
            "SPACE to restart   ·   Esc to quit",
            cx, bottom + end_screen_hint_offset(panel_h, len(stats)), _MUTED,
            font_size=13, anchor_x="center", anchor_y="center",
        )

    # ------------------------------------------------------------------
    # Layout / world <-> screen mapping
    def _sidebar_width(self) -> float:
        sw, _ = self._viewport_size()
        return max(_SIDEBAR_MIN, min(_SIDEBAR_MAX, sw * 0.30))

    def _recompute_layout(self) -> None:
        sw, sh = self._viewport_size()
        sidebar = self._sidebar_width()
        self._layout = build_layout(
            sw, sh, self.session.world, sidebar_width=sidebar
        )

    def _screen_to_world(self, sx: float, sy: float):
        self._ensure_layout()
        if self._layout is None:
            return None
        return self._layout.screen_to_world(sx, sy)

    def _world_to_screen(self, wx: float, wy: float):
        self._ensure_layout()
        if self._layout is None:
            return (0.0, 0.0)
        return self._layout.world_to_screen(wx, wy)

    # ------------------------------------------------------------------
    # Backdrop (start / end screens)
    # ------------------------------------------------------------------
    def _draw_backdrop(self, session: GameSession) -> None:
        sw, sh = self._viewport_size()
        env = session.environment
        light = env.light_level if env is not None else 0.7
        palette = self._sky()

        if light < 0.45:
            visibility = (0.45 - light) / 0.45
            color = _mix(palette.night, palette.star, 0.85 * visibility)
            for i in range(90):
                x = (i * 97.13) % sw
                y = (i * 53.71) % sh
                radius = 1.6 if i % 7 == 0 else 1.0
                arcade.draw_circle_filled(x, y, radius, color)

        celestial = self._celestial(session)
        if celestial is None:
            return

        cx = sw * 0.5
        span = sw * 0.42
        if celestial.sun_visible:
            x = cx - span / 2 + span * celestial.sun_progress
            y = sh - 90 - 40 * math.sin(math.pi * celestial.sun_progress)
            arcade.draw_circle_filled(x, y, 16, palette.sun)
        elif celestial.moon_visible:
            x = cx - span / 2 + span * celestial.moon_progress
            y = sh - 90 - 40 * math.sin(math.pi * celestial.moon_progress)
            arcade.draw_circle_filled(x, y, 13, palette.moon)
            offset = 5 + 8 * (1.0 - celestial.moon_illumination)
            arcade.draw_circle_filled(x + offset, y + 3, 12, _shade(self._sky_color(session), 1.0))

    def _draw_title_panel(
        self, title: str, subtitle: str, hint: str | None = None, accent=_ACCENT
    ) -> None:
        sw, sh = self._viewport_size()
        panel_w = min(620, sw - 60)
        panel_h = 250
        left = (sw - panel_w) / 2
        bottom = (sh - panel_h) / 2
        self._panel(left, bottom, panel_w, panel_h)

        self._text.draw(
            title, sw / 2, bottom + panel_h - 66, accent,
            font_size=44, anchor_x="center", anchor_y="center", bold=True,
        )
        self._text.draw(
            subtitle, sw / 2, bottom + panel_h - 116, _TEXT,
            font_size=19, anchor_x="center", anchor_y="center",
        )
        self._text.draw(
            hint or "Esc: quit   ·   P: pause   ·   Click the world to inspect a cell",
            sw / 2, bottom + 62, _MUTED, font_size=13,
            anchor_x="center", anchor_y="center",
        )

    # ------------------------------------------------------------------
    # World rendering
    # ------------------------------------------------------------------
    def _draw_world(self, session: GameSession) -> None:
        self._ensure_layout()
        layout = self._layout
        if layout is None:
            return
        palette = self._palette()
        env = session.environment
        ambient = self._ambient(session)
        base = _shade(palette.ground, 0.32 + 0.68 * ambient)

        # Fill the whole world panel (right of the sidebar) with ground color
        # so no sky/grey shows around the world when the window is larger than
        # the drawn world (e.g. maximised on a wide screen).
        sw, sh = self._viewport_size()
        panel_left = self._sidebar_width() + _MARGIN
        panel_w = max(1.0, sw - panel_left - _MARGIN)
        panel_h = max(1.0, sh - 2 * _MARGIN)
        arcade.draw_lbwh_rectangle_filled(panel_left, _MARGIN, panel_w, panel_h, base)

        arcade.draw_lbwh_rectangle_filled(
            layout.left, layout.bottom,
            layout.right - layout.left, layout.top - layout.bottom,
            base,
        )

        if env is not None:
            self._draw_weather_cells(session, palette, ambient)
            self._draw_details(session, palette, ambient)
            self._draw_precipitation(session)

        self._draw_barriers(session)
        self._draw_corpses(session)
        self._draw_foods(session)
        self._draw_beans(session)
        self._draw_grid(session)
        self._draw_selection(session)

    def _weather_blocks(self, session: GameSession) -> List[Tuple[int, int, str]]:
        """Block-sampled weather conditions, cached until the field changes.

        The weather strategy rebuilds only every `change_interval` ticks, so the
        per-cell readings are constant in between. Sampling one cell per block
        and caching the result removes thousands of `weather_at` calls per
        frame.
        """
        layout = self._layout
        env = session.environment
        if layout is None or env is None:
            return []
        step = _WEATHER_BLOCK_CELLS
        weather_cfg = getattr(self.sim_config, "weather", None)
        interval = getattr(weather_cfg, "change_interval", None)
        season = getattr(env, "season", None)
        key = (
            env.tick // interval if interval else None,
            season,
            layout.cols,
            layout.rows,
            layout.cell_size,
        )
        if interval and self._weather_blocks_key == key:
            return self._weather_blocks_cache

        world_cell = layout.cell_size
        blocks: List[Tuple[int, int, str]] = []
        for col in range(0, layout.cols, step):
            for row in range(0, layout.rows, step):
                cx = (col + step / 2.0) * world_cell
                cy = (row + step / 2.0) * world_cell
                blocks.append((col, row, env.weather_at(cx, cy)))
        if interval:
            self._weather_blocks_key = key
            self._weather_blocks_cache = blocks
        return blocks

    def _draw_weather_cells(self, session: GameSession, palette, ambient: float) -> None:
        self._ensure_layout()
        layout = self._layout
        if layout is None:
            return
        cell = layout.cell_step
        if cell < 2:
            return

        # Weather tints are coarse blocks that only change when the weather
        # field is rebuilt, so they are built into one reusable shape list
        # instead of one immediate-mode rectangle per block per frame. The tint
        # alpha also depends on ambient light, hence the coarse bucket.
        step = _WEATHER_BLOCK_CELLS
        world_cell = layout.cell_size
        blocks = self._weather_blocks(session)
        tints = _WEATHER_TINT
        alpha_factor = 0.35 + 0.65 * (1.0 - ambient)

        if self._weather_blocks_key is not None:
            key = (
                self._weather_blocks_key,
                int(ambient * 10),
                layout.left,
                layout.bottom,
                layout.scale,
                layout.cols,
                layout.rows,
            )
            if self._weather_shapes_key != key:
                shapes = arcade.shape_list.ShapeElementList()
                for col, row, condition in blocks:
                    tint = tints.get(condition)
                    if tint is None:
                        continue
                    color, alpha = tint
                    a = int(255 * alpha * alpha_factor)
                    if a <= 0:
                        continue
                    sx, sy = layout.world_to_screen(col * world_cell, row * world_cell)
                    block_w = min(step, layout.cols - col) * cell
                    block_h = min(step, layout.rows - row) * cell
                    shapes.append(
                        arcade.shape_list.create_rectangle_filled(
                            sx + block_w / 2.0, sy + block_h / 2.0,
                            block_w, block_h, (*color, a),
                        )
                    )
                self._weather_shapes = shapes
                self._weather_shapes_key = key
            if self._weather_shapes is not None:
                self._weather_shapes.draw()
            return

        # No config to key the cache on: draw directly.
        for col, row, condition in blocks:
            tint = tints.get(condition)
            if tint is None:
                continue
            color, alpha = tint
            a = int(255 * alpha * alpha_factor)
            if a <= 0:
                continue
            sx, sy = layout.world_to_screen(col * world_cell, row * world_cell)
            block_w = min(step, layout.cols - col) * cell
            block_h = min(step, layout.rows - row) * cell
            arcade.draw_lbwh_rectangle_filled(
                sx, sy, block_w, block_h, (*color, a)
            )

    def _draw_details(self, session: GameSession, palette, ambient: float) -> None:
        factor = 0.45 + 0.55 * ambient
        details = palette.details or ((120, 140, 120),)
        layout = self._layout
        key = (
            tuple(details),
            int(factor * 10),
            layout.left if layout else 0.0,
            layout.bottom if layout else 0.0,
            layout.scale if layout else 0.0,
            self._world_width,
            self._world_height,
        )
        if self._detail_shapes_key != key:
            shapes = arcade.shape_list.ShapeElementList()
            for i in range(_DETAIL_COUNT):
                wx = (i * 97.31 + 17.0) % self._world_width
                wy = (i * 57.73 + 29.0) % self._world_height
                sx, sy = self._world_to_screen(wx, wy)
                radius = 1.3 + (i % 4) * 0.5
                shapes.append(
                    arcade.shape_list.create_ellipse_filled(
                        sx, sy, radius * 2, radius * 2,
                        _shade(details[i % len(details)], factor),
                    )
                )
            self._detail_shapes = shapes
            self._detail_shapes_key = key
        if self._detail_shapes is not None:
            self._detail_shapes.draw()

    def _draw_precipitation(self, session: GameSession) -> None:
        self._ensure_layout()
        layout = self._layout
        if layout is None:
            return
        env = session.environment
        if env is None:
            return

        tick = env.tick
        cell = layout.cell_step
        if cell < 3:
            return

        # Same block sampling as the weather tints: precipitation is sparse,
        # so testing one sample per block is enough to place drops. Segments
        # are accumulated and drawn in one batch instead of one call per drop.
        step = _WEATHER_BLOCK_CELLS
        rain: List[Tuple[float, float]] = []
        snow: List[Tuple[float, float]] = []
        for col, row, condition in self._weather_blocks(session):
            if condition not in ("rain", "storm", "snow"):
                continue
            # Only a deterministic subset of blocks draw precipitation so a
            # rainy front never floods the screen with lines.
            if (col * 7 + row * 13 + (tick // 10)) % 3 != 0:
                continue

            sl, sb = layout.cell_screen_rect(col, row)[:2]
            block = cell * step
            count = 2 if condition == "storm" else 1
            speed = 3.4 if condition == "storm" else 2.2

            for i in range(count):
                px = sl + ((i * 37.0 + col * 13.0) % max(1.0, block))
                py = sb + ((tick * speed + i * 41.0 + row * 17.0) % max(1.0, block))
                if condition == "snow":
                    snow.append((px, py))
                else:
                    rain.append((px, py))
                    rain.append((px - 2, py - 8))

        if rain:
            arcade.draw_lines(rain, (170, 200, 240, 160), 1)
        if snow:
            arcade.draw_points(snow, (240, 246, 255, 210), 3)

    def _draw_barriers(self, session: GameSession) -> None:
        """Draw each barrier as a filled, cell-aligned rectangle in its colour.

        Barrier colour comes from the barrier strategy (default yellow); the
        view never hardcodes it.
        """
        self._ensure_layout()
        layout = self._layout
        if layout is None:
            return
        world = session.world
        if world is None:
            return
        for barrier in world.barriers:
            if barrier.kind != "rect":
                continue
            sx, sy = layout.world_to_screen(barrier.x, barrier.y)
            bw = barrier.width * layout.scale
            bh = barrier.height * layout.scale
            color = getattr(barrier, "color", (255, 208, 64))
            arcade.draw_lbwh_rectangle_filled(sx, sy, bw, bh, color)
            arcade.draw_lbwh_rectangle_outline(sx, sy, bw, bh, (0, 0, 0, 110), 1)

    def _draw_corpses(self, session: GameSession) -> None:
        """Draw dead beans as brown points that fade as their energy decays."""
        self._ensure_layout()
        layout = self._layout
        if layout is None:
            return
        corpses = getattr(session, "corpses", None) or []
        if not corpses:
            return

        base = (139, 69, 19)
        points_by_color: Dict[Tuple[int, int, int], List[Tuple[float, float]]] = {}
        for corpse in corpses:
            sx, sy = layout.world_to_screen(corpse.x, corpse.y)
            factor = 0.35 + 0.65 * corpse.energy_ratio
            color = tuple(int(channel * factor) for channel in base)
            points_by_color.setdefault(color, []).append((sx, sy))

        point_size = max(2.0, layout.cell_step * 0.18)
        for color, points in points_by_color.items():
            arcade.draw_points(points, color, point_size)

    def _draw_foods(self, session: GameSession) -> None:
        """Draw food morsels as magenta dots sized by remaining energy.

        Morsels are bucketed into poor/mid/rich tiers so the whole layer
        costs three draw calls. Size grows with energy and brightness never
        drops below a clearly-visible floor, so food reads at a glance
        against any ground colour, day or night.
        """
        self._ensure_layout()
        layout = self._layout
        if layout is None:
            return
        foods = getattr(session, "foods", None) or []
        if not foods:
            return

        food_cfg = getattr(self.sim_config, "food", None)
        base = tuple(food_cfg.color) if food_cfg is not None else (200, 80, 220)
        # One shade and one size per tier: exactly three draw calls for the
        # whole layer, with size and brightness both growing with energy.
        tier_ratio = {0: 1.0 / 6.0, 1: 1.0 / 2.0, 2: 5.0 / 6.0}
        tiers: Dict[int, List[Tuple[float, float]]] = {0: [], 1: [], 2: []}
        for food in foods:
            ratio = food.energy_ratio
            tier = 0 if ratio < 1.0 / 3.0 else (1 if ratio < 2.0 / 3.0 else 2)
            sx, sy = layout.world_to_screen(food.x, food.y)
            tiers[tier].append((sx, sy))

        step = layout.cell_step
        for tier in (0, 1, 2):  # poor first so rich morsels draw on top
            points = tiers[tier]
            if not points:
                continue
            factor = 0.6 + 0.4 * tier_ratio[tier]
            shade = tuple(int(channel * factor) for channel in base)
            size = max(3.0, step * (0.3 + 0.25 * tier))
            arcade.draw_points(points, shade, size)

    def _draw_beans(self, session: GameSession) -> None:
        """Draw beans as colored points using batched `draw_points` (one draw call per color).

        This is significantly faster than the previous per-bean line drawing or
        SpriteList approaches because it submits all points of one color in a
        single GPU instanced draw call.
        """
        self._ensure_layout()
        layout = self._layout
        if layout is None:
            return
        beans = getattr(session, "beans", None) or []
        if not beans:
            return

        # Group points by color (typically 2: male/female, but could be more).
        points_by_color: Dict[Tuple[int, int, int], List[Tuple[float, float]]] = {}
        for bean in beans:
            sx, sy = layout.world_to_screen(bean.x, bean.y)
            points_by_color.setdefault(bean.color, []).append((sx, sy))

        # Point size scales slightly with cell size for visibility.
        point_size = max(2.0, layout.cell_step * 0.15)
        for color, points in points_by_color.items():
            arcade.draw_points(points, color, point_size)
    def _draw_grid(self, session: GameSession) -> None:
        """Draw one line per cell boundary, derived from `world.cell_size`."""
        self._ensure_layout()
        layout = self._layout
        if layout is None:
            return
        step = layout.cell_step
        if step < 6:
            return
        color = _shade(self._palette().ground, 0.55)
        grid_right = layout.left + layout.cols * step
        grid_top = layout.bottom + layout.rows * step

        lines: List[Tuple[float, float]] = []
        for col in range(1, layout.cols):
            sx = layout.left + col * step
            lines.append((sx, layout.bottom))
            lines.append((sx, grid_top))
        for row in range(1, layout.rows):
            sy = layout.bottom + row * step
            lines.append((layout.left, sy))
            lines.append((grid_right, sy))
        if lines:
            arcade.draw_lines(lines, (*color, 90), 1)

        arcade.draw_lbwh_rectangle_outline(
            layout.left, layout.bottom,
            grid_right - layout.left, grid_top - layout.bottom,
            (245, 246, 250, 170), 2,
        )

    def _draw_selection(self, session: GameSession) -> None:
        if self._selected_cell is not None:
            self._draw_cell_marker(self._selected_cell, _INSPECT, 2)
            center = self._cell_center(self._selected_cell)
            if center is not None:
                sx, sy = self._world_to_screen(*center)
                arcade.draw_line(sx - 6, sy, sx + 6, sy, _INSPECT, 1)
                arcade.draw_line(sx, sy - 6, sx, sy + 6, _INSPECT, 1)
        if self._hover_cell is not None and self._hover_cell != self._selected_cell:
            self._draw_cell_marker(self._hover_cell, _HOVER, 1)

    def _draw_cell_marker(self, cell: Tuple[int, int], color, width: float) -> None:
        self._ensure_layout()
        layout = self._layout
        if layout is None:
            return
        col, row = cell
        left, bottom, size, _ = layout.cell_screen_rect(col, row)
        arcade.draw_lbwh_rectangle_outline(left, bottom, size, size, color, width)

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------
    def _panel(self, left: float, bottom: float, width: float, height: float):
        arcade.draw_lbwh_rectangle_filled(left, bottom, width, height, _PANEL_BG)
        arcade.draw_lbwh_rectangle_outline(left, bottom, width, height, _PANEL_BORDER, 1)

    def _box(self, left: float, top: float, width: float, height: float, title: str):
        bottom = top - height
        self._panel(left, bottom, width, height)
        self._text.draw(
            title.upper(), left + 12, top - 16, _DIM,
            font_size=10, bold=True,
        )
        return bottom

    def _bar(self, left: float, bottom: float, width: float, height: float,
             fraction: float, color) -> None:
        arcade.draw_lbwh_rectangle_filled(left, bottom, width, height, _TRACK)
        filled = max(0.0, min(1.0, fraction)) * width
        if filled > 0:
            arcade.draw_lbwh_rectangle_filled(left, bottom, filled, height, color)

    def _draw_sidebar(self, session: GameSession) -> None:
        _, sh = self._viewport_size()
        world = session.world
        env = session.environment
        calendar = env.calendar if env is not None else None
        palette = self._palette()

        left = _MARGIN
        width = self._sidebar_width() - _MARGIN
        controls_h = _CONTROLS_BOX_H
        limit = _MARGIN + controls_h + _GAP
        cursor = sh - _MARGIN

        def take(height: float):
            """Reserve a box at the top of the remaining stack."""
            nonlocal cursor
            if cursor - height < limit:
                return None
            box_top = cursor
            cursor = box_top - height - _GAP
            return box_top, box_top - height

        # ---- Time -----------------------------------------------------
        h = _TIME_BOX_H
        slot = take(h)
        if slot is not None:
            top, bottom = slot
            self._box(left, top, width, h, "Time")
            tick = session.clock.tick
            day = calendar.day if calendar is not None else 1
            year = calendar.year if calendar is not None else 1
            clock = calendar.clock if calendar is not None else "--:--"
            self._text.draw(
                f"Day {day}   ·   {clock}", left + 12, top - 40, _TEXT,
                font_size=17, bold=True,
            )
            self._text.draw(
                f"Year {year}   ·   tick {tick}   ·   sim {self._format_sim_time(tick)}",
                left + 12, top - 62, _MUTED, font_size=11,
            )
            self._text.draw(
                f"{palette.name}   ·   {self._phase(session)}",
                left + 12, top - 80,
                _season_color(palette, self._ambient(session)), font_size=12,
            )

        # ---- Day ------------------------------------------------------
        h = _DAY_BOX_H
        slot = take(h)
        if slot is not None:
            top, bottom = slot
            self._box(left, top, width, h, "Day")
            fraction = calendar.day_fraction if calendar is not None else 0.0
            light = self._light(session)
            self._text.draw(
                f"light {light:.0%}", left + width - 12, top - 16,
                _MUTED, font_size=11, anchor_x="right",
            )
            self._bar(left + 12, top - 34, width - 24, 6, fraction, _SUN)
            self._text.draw("00", left + 12, top - 50, _DIM, font_size=9)
            self._text.draw("12", left + width / 2, top - 50, _DIM, font_size=9,
                            anchor_x="center")
            self._text.draw("24", left + width - 12, top - 50, _DIM, font_size=9,
                            anchor_x="right")
            self._draw_sun_track(session, left + 12, top - 84, width - 24, 22)

        # ---- Season (independent of the day bar) ----------------------
        h = _SEASON_BOX_H
        slot = take(h)
        if slot is not None:
            top, bottom = slot
            self._box(left, top, width, h, "Season")
            self._text.draw(
                palette.name, left + 12, top - 38, _TEXT, font_size=18, bold=True,
            )
            if calendar is not None:
                info = (f"day {calendar.day_of_season} of {calendar.days_per_season}"
                        f"   ·   year {calendar.year}")
            else:
                info = "static"
            self._text.draw(info, left + 12, top - 58, _MUTED, font_size=11)
            progress = calendar.season_progress if calendar is not None else 0.0
            self._bar(left + 12, top - 72, width - 24, 6, progress, (140, 220, 150))

        # ---- Environment at the inspected point -----------------------
        h = _ENVIRONMENT_BOX_H
        slot = take(h)
        if slot is not None:
            top, bottom = slot
            self._box(left, top, width, h, "Environment")
            target, label = self._reading(session)
            if env is not None:
                condition = env.weather_at(target[0], target[1])
                self._text.draw(
                    f"{label}   {env.light_at(target[0], target[1]):.0%} light"
                    f"   ·   {condition}",
                    left + 12, top - 38, _WEATHER_LABEL.get(condition, _TEXT),
                    font_size=13,
                )
                self._text.draw(
                    f"{env.temperature_at(target[0], target[1]):.1f} °C"
                    f"    {env.humidity_at(target[0], target[1]):.0%} RH"
                    f"    {env.pressure_at(target[0], target[1]):.0f} hPa",
                    left + 12, top - 62, _TEXT, font_size=13,
                )
                self._text.draw(
                    f"climate: {palette.base_temperature:.0f} ± "
                    f"{palette.temperature_swing:.0f} °C   ·   {palette.name}",
                    left + 12, top - 84, _MUTED, font_size=11,
                )
                self._text.draw(
                    f"ground: {palette.ground_meaning}",
                    left + 12, top - 100, _DIM, font_size=9,
                )
                self._text.draw(
                    "click a cell to pin it", left + 12, top - 116, _DIM,
                    font_size=10,
                )
            else:
                self._text.draw(
                    "no environment", left + 12, top - 42, _MUTED, font_size=13,
                )
                self._text.draw(
                    "click a cell to pin it", left + 12, top - 62, _DIM,
                    font_size=10,
                )

        # ---- Inspector ------------------------------------------------
        h = _INSPECTOR_BOX_H
        slot = take(h)
        if slot is not None:
            top, bottom = slot
            self._box(left, top, width, h, "Inspector")
            cell_y, contents_y, temperature_y, readings_y, condition_y = (
                inspector_geometry(left, width, top)
            )
            if self._selected_cell is not None and env is not None:
                col, row = self._selected_cell
                wx, wy = self._cell_center((col, row))
                condition = env.weather_at(wx, wy)
                self._text.draw(
                    f"cell ({col}, {row})   ·   x {wx:.0f}  y {wy:.0f}",
                    left + 12, cell_y, _MUTED, font_size=11,
                )
                # Cell contents: bean / barrier / empty
                beans = getattr(session, "beans", None) or []
                bean_at = None
                for b in beans:
                    if abs(b.x - wx) < 1.0 and abs(b.y - wy) < 1.0:
                        bean_at = b
                        break
                barriers = getattr(world, "barriers", None) or []
                barrier_at = None
                for b in barriers:
                    if b.kind == "rect":
                        if (b.x <= wx <= b.x + b.width and b.y <= wy <= b.y + b.height):
                            barrier_at = b
                            break
                if bean_at is not None:
                    self._text.draw(
                        f"BEAN   ·   gender={bean_at.gender}   ·   colour={bean_at.color}",
                        left + 12, contents_y, _ACCENT, font_size=11,
                    )
                elif barrier_at is not None:
                    self._text.draw(
                        f"BARRIER   ·   kind={barrier_at.kind}   ·   colour={barrier_at.color}",
                        left + 12, contents_y, _MUTED, font_size=11,
                    )
                else:
                    self._text.draw(
                        "EMPTY", left + 12, contents_y, _DIM, font_size=11,
                    )
                # The large temperature and the small RH/pressure/light line
                # live on separate baselines so they can never overlap.
                self._text.draw(
                    f"{env.temperature_at(wx, wy):.1f} °C", left + 12, temperature_y,
                    _TEXT, font_size=22, bold=True,
                )
                self._text.draw(
                    f"{env.humidity_at(wx, wy):.0%} RH   ·   "
                    f"{env.pressure_at(wx, wy):.0f} hPa   ·   "
                    f"{env.light_at(wx, wy):.0%} light",
                    left + 12, readings_y, _TEXT, font_size=11,
                )
                self._text.draw(
                    condition, left + width - 12, condition_y,
                    _WEATHER_LABEL.get(condition, _TEXT), font_size=13,
                    anchor_x="right",
                )
            else:
                self._text.draw(
                    "Click any cell in the world", left + 12, top - 44,
                    _TEXT, font_size=13,
                )
                self._text.draw(
                    "to read its temperature, light,", left + 12, top - 64,
                    _MUTED, font_size=11,
                )
                self._text.draw(
                    "humidity and pressure.", left + 12, top - 82,
                    _MUTED, font_size=11,
                )

        # ---- Food census ----------------------------------------------
        h = _FOOD_BOX_H
        slot = take(h)
        if slot is not None:
            top, bottom = slot
            self._box(left, top, width, h, "Food")
            self._draw_food_census(session, left + 12, top, width - 24)

        # ---- Weather field (fills the remaining stack, capped) ------------
        remaining = cursor - limit
        if remaining >= 80 and env is not None and world is not None:
            top = cursor
            # Cap the box height so it never swallows the sidebar on tall
            # windows; census rows are limited by box height anyway.
            h = min(remaining, 220)
            self._box(left, top, width, h, "Weather field")
            self._draw_weather_census(session, left + 12, top - 34, width - 24, h)
            cursor = top - h - _GAP

        # ---- Beans census -------------------------------------------
        remaining = max(0, cursor - limit)
        if remaining >= 80:
            top = cursor
            h = min(remaining, 180)
            self._box(left, top, width, h, "Beans Census")
            self._draw_beans_census(session, left + 12, top - 34, width - 24)
            cursor = top - h - _GAP

        # ---- Controls (anchored to the bottom of the sidebar) ---------
        # Vertical order, top to bottom: button, keys, slider. Each block owns
        # a reserved band (see `controls_geometry`) so no two widgets can ever
        # share pixels.
        box_bottom = _MARGIN
        box_top, button_rect, keys_top, slider_rect = controls_geometry(
            left, width, box_bottom,
        )
        self._box(left, box_top, width, _CONTROLS_BOX_H, "Controls")

        # ---- Configurations button: first row under the title ----
        btn_x, btn_y, btn_w, btn_h = button_rect
        self._config_rect = button_rect
        hover = _point_in_rect(
            self._last_mouse_x, self._last_mouse_y, self._config_rect,
        )
        btn_color = _ACCENT if hover else _MUTED
        arcade.draw_lbwh_rectangle_filled(btn_x, btn_y, btn_w, btn_h, _PANEL_BG)
        arcade.draw_lbwh_rectangle_outline(
            btn_x, btn_y, btn_w, btn_h, btn_color, 1,
        )
        self._text.draw(
            "Configurations", btn_x + 8, btn_y + 7, btn_color, font_size=10,
        )

        # ---- Key bindings, below the button ----
        lines = [
            ("SPACE", "start / restart"),
            ("P", "pause / resume"),
            ("C", "config screen"),
            ("Esc / Q", "quit"),
            ("Click", "inspect cell"),
        ]
        y = keys_top
        for key, action in lines:
            self._text.draw(key, left + 12, y, _ACCENT, font_size=11, bold=True)
            self._text.draw(action, left + 96, y, _MUTED, font_size=11)
            y -= _KEY_ROW_H

        # ---- Playback-speed slider: own band at the very bottom ----
        track_x, slider_y, track_w, track_h = slider_rect
        self._slider_rect = slider_rect

        scale = session.clock.time_scale
        fraction = (scale - _TIME_SCALE_MIN) / max(1e-6, _TIME_SCALE_MAX - _TIME_SCALE_MIN)
        fraction = max(0.0, min(1.0, fraction))
        thumb_x = track_x + fraction * track_w - _SLIDER_THUMB_W / 2.0

        # Label sits above the track, inside the slider band only.
        self._text.draw(
            f"Speed {scale:.2f}x  (drag)",
            track_x, slider_y + track_h + 6, _MUTED, font_size=10,
        )
        arcade.draw_lbwh_rectangle_filled(
            track_x, slider_y, track_w, track_h, _SLIDER_TRACK,
        )
        filled = fraction * track_w
        if filled > 0:
            arcade.draw_lbwh_rectangle_filled(
                track_x, slider_y, filled, track_h, _SLIDER_TRACK_FILLED,
            )
        arcade.draw_lbwh_rectangle_filled(
            thumb_x, slider_y - 2, _SLIDER_THUMB_W, track_h + 4, _SLIDER_THUMB,
        )
        arcade.draw_lbwh_rectangle_outline(
            thumb_x, slider_y - 2, _SLIDER_THUMB_W, track_h + 4,
            _SLIDER_THUMB_EDGE, 1,
        )

    def _draw_weather_census(self, session: GameSession, left: float, top: float,
                             width: float, box_height: float) -> None:
        """How many cells show each condition: proves the field is not uniform."""
        env = session.environment
        if env is None:
            return

        weather_strategy = env.weather_strategy
        if weather_strategy is None:
            return

        cache_key = (
            self._cols,
            self._rows,
            getattr(weather_strategy, "_interval", None),
            env.weather,
            env.season,
        )
        if cache_key != self._census_cache:
            counts = {name: 0 for name in _WEATHER_LABEL}
            for col in range(self._cols):
                for row in range(self._rows):
                    condition = weather_strategy.weather_at_cell(col, row)
                    counts[condition] = counts.get(condition, 0) + 1
            self._census_cache = cache_key
            self._census_counts = counts

        counts = self._census_counts
        total = max(1, self._cols * self._rows)
        present = [(name, count) for name, count in counts.items() if count > 0]
        present.sort(key=lambda item: item[1], reverse=True)

        # Rows start at top-34; leave a little padding at the bottom.
        available = max(1, int((box_height - 40) // 17))
        shown = present[:available]
        hidden = len(present) - len(shown)

        y = top
        for condition, count in shown:
            color = _WEATHER_LABEL.get(condition, _TEXT)
            arcade.draw_lbwh_rectangle_filled(left, y - 1, 8, 8, color)
            self._text.draw(condition, left + 16, y, _TEXT, font_size=11)
            self._text.draw(
                f"{count:>3} cells   ·   {count / total:>4.0%}",
                left + width, y, _MUTED, font_size=11, anchor_x="right",
            )
            y -= 17

        if hidden > 0:
            self._text.draw(
                f"+{hidden} more condition{'s' if hidden != 1 else ''}",
                left + 16, y, _DIM, font_size=10,
            )

    def _food_abundance(self, session: GameSession) -> float:
        """Seasonal food-abundance multiplier from the environment's sun profile."""
        env = session.environment
        if env is None:
            return 1.0
        solar = env.solar
        return _seasonal_abundance(solar.sun_intensity, solar.daylight_fraction)

    def _draw_food_census(self, session: GameSession, left: float, top: float,
                          width: float) -> None:
        """Food census: morsel count, energy vs the seasonal target and top-up cadence."""
        foods = getattr(session, "foods", None) or []
        config = getattr(self.sim_config, "food", None)
        target = getattr(config, "target_total_energy", 0.0) if config else 0.0
        interval = getattr(config, "top_up_interval_ticks", 0) if config else 0
        abundance = self._food_abundance(session)
        effective_target = target * abundance
        energy = _food_total_energy(foods)
        count = len(foods)
        average = energy / count if count else 0.0
        count_y, energy_y, bar_y, top_up_y = food_geometry(left, width, top)

        self._text.draw(
            f"Morsels {count}   ·   avg {average:.0f} E",
            left, count_y, _TEXT, font_size=11,
        )
        self._text.draw(
            f"Energy {energy:.0f} / {effective_target:.0f}",
            left, energy_y, _TEXT, font_size=11,
        )
        self._bar(
            left, bar_y, width, 6,
            energy / effective_target if effective_target > 0 else 0.0, _ACCENT,
        )
        self._text.draw(
            f"Top-up every {interval} ticks   ·   ×{abundance:.2f}",
            left, top_up_y, _MUTED, font_size=10,
        )

    def _draw_beans_census(self, session: GameSession, left: float, top: float,
                            width: float) -> None:
        """Bean census: initial, alive, and dead counts by gender."""
        beans = getattr(session, "beans", None) or []
        corpses = getattr(session, "corpses", None) or []
        if not beans and not corpses:
            self._text.draw(
                "no beans", left, top, _DIM, font_size=11,
            )
            return

        # Initial counts (stored at spawn)
        initial_female = getattr(session, "initial_female", 0)
        initial_male = getattr(session, "initial_male", 0)

        # Current alive/dead counts
        alive_female = sum(1 for b in beans if b.gender == "female")
        alive_male = len(beans) - alive_female
        dead_female = max(0, initial_female - alive_female)
        dead_male = max(0, initial_male - alive_male)

        y = top

        # Header row
        self._text.draw("Gender", left, y, _ACCENT, font_size=11, bold=True)
        self._text.draw("Initial", left + 80, y, _ACCENT, font_size=11, bold=True)
        self._text.draw("Alive", left + 160, y, _ACCENT, font_size=11, bold=True)
        self._text.draw("Dead", left + 240, y, _ACCENT, font_size=11, bold=True)
        y -= 17

        # Female row
        color_f = (255, 64, 64)  # red
        arcade.draw_lbwh_rectangle_filled(left, y - 1, 8, 8, color_f)
        self._text.draw("Female", left + 16, y, _TEXT, font_size=11)
        self._text.draw(f"{initial_female:>3}", left + 80, y, _TEXT, font_size=11)
        self._text.draw(f"{alive_female:>3}", left + 160, y, _TEXT, font_size=11)
        self._text.draw(f"{dead_female:>3}", left + 240, y, _TEXT, font_size=11)
        y -= 17

        # Male row
        color_m = (0, 128, 255)  # blue
        arcade.draw_lbwh_rectangle_filled(left, y - 1, 8, 8, color_m)
        self._text.draw("Male", left + 16, y, _TEXT, font_size=11)
        self._text.draw(f"{initial_male:>3}", left + 80, y, _TEXT, font_size=11)
        self._text.draw(f"{alive_male:>3}", left + 160, y, _TEXT, font_size=11)
        self._text.draw(f"{dead_male:>3}", left + 240, y, _TEXT, font_size=11)
        y -= 17

        # Total row
        total_initial = initial_female + initial_male
        total_alive = alive_female + alive_male
        total_dead = dead_female + dead_male
        self._text.draw("Total", left + 16, y, _ACCENT, font_size=11, bold=True)
        self._text.draw(f"{total_initial:>3}", left + 80, y, _ACCENT, font_size=11, bold=True)
        self._text.draw(f"{total_alive:>3}", left + 160, y, _ACCENT, font_size=11, bold=True)
        self._text.draw(f"{total_dead:>3}", left + 240, y, _ACCENT, font_size=11, bold=True)

        if corpses:
            y -= 17
            self._text.draw(
                f"Corpses remaining: {len(corpses)}",
                left + 16, y, _MUTED, font_size=11,
            )

        # End simulation message if no alive beans
        if total_alive == 0 and total_initial > 0:
            y -= 20
            self._text.draw(
                "Population extinct. Simulation ended.",
                left, y, _ACCENT, font_size=11, bold=True,
            )
            y -= 15
            self._text.draw(
                f"Duration: {session.clock.tick} ticks ({session.clock.tick/30:.1f}s)",
                left, y, _MUTED, font_size=10,
            )
            y -= 13
            self._text.draw(
                f"Season: {session.environment.season if session.environment else 'N/A'}",
                left, y, _MUTED, font_size=10,
            )

    def _draw_sun_track(self, session: GameSession, left: float, bottom: float,
                        width: float, height: float) -> None:
        celestial = self._celestial(session)
        if celestial is None:
            return
        palette = self._sky()

        arcade.draw_line(left, bottom, left + width, bottom, (*_DIM, 120), 1)

        def position(progress: float):
            x = left + width * max(0.0, min(1.0, progress))
            y = bottom + 2 + height * 0.8 * math.sin(math.pi * progress)
            return x, y

        if celestial.sun_visible:
            x, y = position(celestial.sun_progress)
            arcade.draw_circle_filled(x, y, 6, palette.sun)
        elif celestial.moon_visible:
            x, y = position(celestial.moon_progress)
            arcade.draw_circle_filled(x, y, 5, palette.moon)
            shadow = 7 * (1.0 - celestial.moon_illumination)
            if shadow > 0.5:
                arcade.draw_circle_filled(
                    x + shadow * 0.6, y, 4.4, _shade(self._sky_color(session), 0.7)
                )

    def _format_sim_time(self, ticks: int) -> str:
        total = ticks / self._tick_rate
        minutes = int(total // 60)
        seconds = total % 60
        return f"{minutes:02d}:{seconds:04.1f}"

    # ------------------------------------------------------------------
    # Arcade window events
    # ------------------------------------------------------------------
    def on_draw(self) -> None:
        # Two windows can exist at once (main + config). Arcade's draw calls
        # use the module-global active window, so each window claims it while
        # drawing its own frame.
        arcade.set_window(self)
        self._ensure_layout()
        state = self.session.state
        if state in (GameState.START, GameState.END):
            self._selected_cell = None
            self._hover_cell = None
        if state == GameState.START:
            self.draw_start_screen()
        elif state == GameState.PLAYING:
            self.draw_playing(self.session)
        elif state == GameState.PAUSED:
            self.draw_paused(self.session)
        elif state == GameState.CONFIG:
            # Keep the world visible behind the separate config window.
            self.draw_playing(self.session)
            self._open_config_window()
        elif state == GameState.END:
            self.draw_end_screen(self.session)
        # pyglet's Window.draw() calls flip() (glXSwapBuffers) after on_draw.

    def on_resize(self, width: int, height: int) -> None:
        super().on_resize(width, height)
        self._layout_size = None
        self._recompute_layout()
        logger.info(
            "event=ui.window_resized width=%s height=%s", width, height
        )

    def _open_config_window(self) -> None:
        """Open the config window once; ignore repeated requests."""
        if self._config_window is not None:
            return
        self.session.state = GameState.CONFIG
        self._config_window = ConfigWindow(
            self.session, self.session.world, self.sim_config,
            on_closed=self._on_config_closed,
        )

    def _on_config_closed(self) -> None:
        self._config_window = None
        # Closing the config window clears Arcade's global "active window";
        # restore the main window so the next frame has a draw target.
        arcade.set_window(self)
        if self.session.state == GameState.CONFIG:
            self.session.state = GameState.PLAYING

    def _slider_hit(self, sx: float, sy: float) -> bool:
        if self._slider_rect is None:
            return False
        lx, ly, lw, lh = self._slider_rect
        scale = self.session.clock.time_scale
        fraction = (scale - _TIME_SCALE_MIN) / max(1e-6, _TIME_SCALE_MAX - _TIME_SCALE_MIN)
        fraction = max(0.0, min(1.0, fraction))
        thumb_w = 10
        thumb_x = lx + fraction * lw - thumb_w / 2.0
        # Generous vertical band so the thin track is easy to grab; it stays
        # inside the slider's own row and never reaches the button above.
        track = (lx, ly - 8, lw, lh + 16)
        thumb_rect = (thumb_x, ly - 8, thumb_w, lh + 16)
        return _point_in_rect(sx, sy, track) or _point_in_rect(sx, sy, thumb_rect)

    def _slider_scale_from_x(self, sx: float) -> float:
        if self._slider_rect is None:
            return self.session.clock.time_scale
        lx, ly, lw, lh = self._slider_rect
        fraction = (sx - lx) / max(1e-6, lw)
        fraction = max(0.0, min(1.0, fraction))
        return _TIME_SCALE_MIN + fraction * (_TIME_SCALE_MAX - _TIME_SCALE_MIN)

    def _apply_slider_scale(self, sx: float) -> None:
        """Set playback speed via the input handler (perception only)."""
        value = self._slider_scale_from_x(sx)
        handler = self._input
        if handler is not None and hasattr(handler, "set_time_scale"):
            handler.set_time_scale(value)
        else:
            from sim.time.game_clock import set_time_scale
            set_time_scale(self.session.clock, value, vmin=_TIME_SCALE_MIN, vmax=_TIME_SCALE_MAX)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> None:
        sx, sy = self._mouse_to_screen(x, y)
        self._last_mouse_x = sx
        self._last_mouse_y = sy
        if self._slider_dragging and self._slider_rect is not None:
            self._apply_slider_scale(sx)
            return
        if self.session.state in (GameState.PLAYING, GameState.PAUSED):
            world_xy = self._screen_to_world(sx, sy)
            world = self.session.world
            if world_xy is not None and world is not None:
                self._hover_cell = world.cell_index(*world_xy)
            else:
                self._hover_cell = None
        else:
            self._hover_cell = None

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> None:
        if self.session.state not in (GameState.PLAYING, GameState.PAUSED):
            return
        sx, sy = self._mouse_to_screen(x, y)
        # Config button (in Controls box): opens the separate config window.
        if self._config_rect is not None and _point_in_rect(
            sx, sy, self._config_rect
        ):
            self._open_config_window()
            return
        # Playback-speed slider: press anywhere on the track starts a drag.
        if self._slider_hit(sx, sy):
            self._slider_dragging = True
            self._apply_slider_scale(sx)
            return
        self._slider_dragging = False
        world_xy = self._screen_to_world(sx, sy)
        world = self.session.world
        if world_xy is not None and world is not None:
            cell = world.cell_index(*world_xy)
            self._selected_cell = cell
            env = self.session.environment
            if env is not None:
                cx, cy = world.cell_center(*cell)
                logger.info(
                    "event=ui.cell_inspected cell=(%d,%d) x=%.0f y=%.0f "
                    "weather=%s temperature=%.1f humidity=%.2f pressure=%.1f light=%.2f",
                    cell[0], cell[1], cx, cy,
                    env.weather_at(cx, cy),
                    env.temperature_at(cx, cy),
                    env.humidity_at(cx, cy),
                    env.pressure_at(cx, cy),
                    env.light_at(cx, cy),
                )
        elif button == arcade.MOUSE_BUTTON_LEFT:
            self._selected_cell = None

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> None:
        self._slider_dragging = False


def _season_color(palette: SeasonPalette, ambient: float):
    """Readable text colour derived from the season ground colour."""
    return _mix(_shade(palette.ground, 0.6 + 0.4 * ambient), (255, 255, 255), 0.45)

class ConfigWindow(arcade.Window):
    """A separate window showing all simulation configuration parameters."""

    def __init__(
        self,
        session: GameSession,
        world: World,
        config: SimulationConfig,
        on_closed=None,
    ):
        super().__init__(width=1200, height=880, title="Bean World - Configuration")
        self.session = session
        self.sim_config = config
        self._on_closed = on_closed
        self._text_cache: Dict[tuple, "arcade.Text"] = {}

    def on_draw(self) -> None:
        arcade.set_window(self)
        self.clear((8, 12, 20))
        self._draw_config_screen()

    def on_close(self) -> None:
        self.close()

    def close(self) -> None:
        # Reset the game state exactly once, whether the window was closed by
        # ESC/Q, the window manager, or programmatically.
        callback, self._on_closed = self._on_closed, None
        super().close()
        if callback is not None:
            callback()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol in (arcade.key.ESCAPE, arcade.key.Q):
            self.close()

    def _text_draw(
        self,
        text: str,
        x: float,
        y: float,
        color,
        font_size: float = 12,
        anchor_x: str = "left",
        anchor_y: str = "baseline",
        bold: bool = False,
    ) -> "arcade.Text":
        text = str(text)
        color = tuple(color)
        key = (text, color, float(font_size), anchor_x, anchor_y, bold)
        item = self._text_cache.get(key)
        if item is None:
            if len(self._text_cache) >= 512:
                self._text_cache.clear()
            item = arcade.Text(
                text, x, y, color=color, font_size=font_size,
                anchor_x=anchor_x, anchor_y=anchor_y, bold=bold,
            )
            self._text_cache[key] = item
        else:
            item.x = x
            item.y = y
        item.draw()
        return item

    def _draw_config_screen(self) -> None:
        """Render every config dataclass field, grouped by top-level topic.

        The field list is generated from the dataclasses themselves, so a new
        config field shows up here automatically instead of being forgotten.
        """
        sw, sh = self.width, self.height
        cfg = self.sim_config

        sections = []
        for f in fields(cfg):
            value = getattr(cfg, f.name)
            if is_dataclass(value):
                sections.append((f.name, _config_rows(value)))
            elif isinstance(value, (list, tuple)) and value and is_dataclass(value[0]):
                rows = []
                for index, item in enumerate(value):
                    for key, text in _config_rows(item):
                        rows.append((f"[{index}] {key}", text))
                sections.append((f.name, rows))
            elif isinstance(value, (bool, int, float, str)):
                sections.append(
                    (f.name, [(f.name, _format_config_value(value))])
                )

        self._text_draw(
            "CONFIGURATION", 20, sh - 26, _ACCENT, font_size=18, bold=True,
        )
        self._text_draw(
            "generated from the config dataclasses   ·   C / ESC / Q to close",
            20, sh - 46, _MUTED, font_size=10,
        )

        columns = 3
        col_gap = 18.0
        col_w = (sw - 2 * 20 - (columns - 1) * col_gap) / columns
        line_h = 15.0
        section_gap = 10.0
        title_h = 18.0
        top = sh - 72

        # Balance the sections across columns by total height.
        per_column = [[] for _ in range(columns)]
        heights = [0.0] * columns
        for title, rows in sections:
            height = title_h + len(rows) * line_h + section_gap
            target = heights.index(min(heights))
            per_column[target].append((title, rows))
            heights[target] += height

        for index, column in enumerate(per_column):
            x = 20.0 + index * (col_w + col_gap)
            y = top
            for title, rows in column:
                self._text_draw(
                    title.upper(), x, y, _ACCENT, font_size=12, bold=True,
                )
                y -= title_h
                for key, text in rows:
                    if y < 12:
                        break
                    self._text_draw(
                        _clip(key, 26), x, y, _MUTED, font_size=10,
                    )
                    self._text_draw(
                        _clip(text, 30), x + 170, y, _TEXT, font_size=10,
                    )
                    y -= line_h
                y -= section_gap
