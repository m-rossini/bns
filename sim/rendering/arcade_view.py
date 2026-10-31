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
from typing import Dict, Optional, Tuple

import arcade

from sim.components import GameSession, GameState
from sim.domain.visuals import SeasonPalette, SkyPalette
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

_MARGIN = 12.0
_GAP = 8.0
_SIDEBAR_MIN = 300.0
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
    ):
        super().__init__(width, height, title, resizable=True)
        self.session = session
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
        self._draw_title_panel(
            "GAME OVER",
            f"Reason: {session.end_reason or 'ended'}",
            hint="SPACE to restart   ·   Esc to quit",
            accent=(240, 96, 96),
        )

    # ------------------------------------------------------------------
    # Layout / world <-> screen mapping
    # ------------------------------------------------------------------
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
        self._draw_grid(session)
        self._draw_selection(session)

    def _draw_weather_cells(self, session: GameSession, palette, ambient: float) -> None:
        self._ensure_layout()
        layout = self._layout
        if layout is None:
            return
        env = session.environment
        if env is None:
            return
        cell = layout.cell_step
        if cell < 2:
            return

        for col in range(layout.cols):
            for row in range(layout.rows):
                cx, cy = layout.cell_center(col, row)
                wx, wy = layout.world_to_screen(cx, cy)
                tint = _WEATHER_TINT.get(env.weather_at(cx, cy))
                if tint is None:
                    continue
                color, alpha = tint
                a = int(255 * alpha * (0.35 + 0.65 * (1.0 - ambient)))
                arcade.draw_lbwh_rectangle_filled(
                    wx - cell / 2, wy - cell / 2, cell, cell, (*color, max(0, a))
                )

    def _draw_details(self, session: GameSession, palette, ambient: float) -> None:
        factor = 0.45 + 0.55 * ambient
        details = palette.details or ((120, 140, 120),)
        for i in range(150):
            wx = (i * 97.31 + 17.0) % self._world_width
            wy = (i * 57.73 + 29.0) % self._world_height
            sx, sy = self._world_to_screen(wx, wy)
            radius = 1.3 + (i % 4) * 0.5
            arcade.draw_circle_filled(
                sx, sy, radius, _shade(details[i % len(details)], factor)
            )

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

        for col in range(layout.cols):
            for row in range(layout.rows):
                cx, cy = layout.cell_center(col, row)
                condition = env.weather_at(cx, cy)
                if condition not in ("rain", "storm", "snow"):
                    continue
                # Only a deterministic subset of cells draw precipitation so a
                # rainy front never floods the screen with lines.
                if (col * 7 + row * 13 + (tick // 10)) % 3 != 0:
                    continue

                sl, sb = layout.cell_screen_rect(col, row)[:2]
                count = 2 if condition == "storm" else 1
                speed = 3.4 if condition == "storm" else 2.2

                for i in range(count):
                    px = sl + ((i * 37.0 + col * 13.0) % max(1.0, cell))
                    py = sb + ((tick * speed + i * 41.0 + row * 17.0) % max(1.0, cell))
                    if condition == "snow":
                        arcade.draw_circle_filled(px, py, 1.6, (240, 246, 255, 210))
                    else:
                        arcade.draw_line(
                            px, py, px - 2, py - 8, (170, 200, 240, 160), 1
                        )

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

        for col in range(1, layout.cols):
            sx = layout.left + col * step
            arcade.draw_line(sx, layout.bottom, sx, grid_top, (*color, 90), 1)
        for row in range(1, layout.rows):
            sy = layout.bottom + row * step
            arcade.draw_line(layout.left, sy, grid_right, sy, (*color, 90), 1)

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
        controls_h = 96
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
        h = 92
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
        h = 96
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
        h = 84
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
        h = 128
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
                    f"ground ({palette.ground_meaning}): "
                    f"{palette.name.lower()} colour, season-driven not random",
                    left + 12, top - 102, _DIM, font_size=9,
                )
            else:
                self._text.draw(
                    "no environment", left + 12, top - 42, _MUTED, font_size=13,
                )
            self._text.draw(
                "click a cell to pin it", left + 12, top - 108, _DIM, font_size=10,
            )

        # ---- Inspector ------------------------------------------------
        h = 116
        slot = take(h)
        if slot is not None:
            top, bottom = slot
            self._box(left, top, width, h, "Inspector")
            if self._selected_cell is not None and env is not None:
                col, row = self._selected_cell
                wx, wy = self._cell_center((col, row))
                condition = env.weather_at(wx, wy)
                self._text.draw(
                    f"cell ({col}, {row})   ·   x {wx:.0f}  y {wy:.0f}",
                    left + 12, top - 38, _MUTED, font_size=11,
                )
                self._text.draw(
                    f"{env.temperature_at(wx, wy):.1f} °C", left + 12, top - 70,
                    _TEXT, font_size=24, bold=True,
                )
                self._text.draw(
                    f"{env.humidity_at(wx, wy):.0%} RH   ·   "
                    f"{env.pressure_at(wx, wy):.0f} hPa   ·   "
                    f"{env.light_at(wx, wy):.0%} light",
                    left + 12, top - 92, _TEXT, font_size=11,
                )
                self._text.draw(
                    condition, left + width - 12, top - 68,
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

        # ---- Weather field (fills the remaining stack, capped) ------------
        remaining = cursor - limit
        if remaining >= 80 and env is not None and world is not None:
            top = cursor
            # Cap the box height so it never swallows the sidebar on tall
            # windows; census rows are limited by box height anyway.
            h = min(remaining, 220)
            self._box(left, top, width, h, "Weather field")
            self._draw_weather_census(session, left + 12, top - 34, width - 24, h)

        # ---- Controls (anchored to the bottom of the sidebar) ---------
        # Box height gives each key its own row plus a dedicated slider row
        # at the bottom, so nothing overlaps or clips against the window edge.
        h = 160
        box_bottom = _MARGIN
        box_top = box_bottom + h
        self._box(left, box_top, width, h, "Controls")
        lines = [
            ("SPACE", "start / restart"),
            ("P", "pause / resume"),
            ("Esc / Q", "quit"),
            ("Click", "inspect cell"),
        ]
        # Stack keys from the top down with even spacing.
        y = box_top - 34
        for key, action in lines:
            self._text.draw(key, left + 12, y, _ACCENT, font_size=11, bold=True)
            self._text.draw(action, left + 96, y, _MUTED, font_size=11)
            y -= 20

        # ---- Playback-speed slider (dedicated row at the bottom) ----
        # Slows/speeds the *perceived* ticker only; sim time progression
        # (tick_rate, clock.tick) is unchanged. Value comes from config.
        slider_y = box_bottom + 14      # track, with padding above box edge
        track_w = width - 24
        track_h = 6
        track_x = left + 12
        thumb_w = 10
        scale = session.clock.time_scale
        fraction = (scale - _TIME_SCALE_MIN) / max(1e-6, _TIME_SCALE_MAX - _TIME_SCALE_MIN)
        fraction = max(0.0, min(1.0, fraction))
        thumb_x = track_x + fraction * track_w - thumb_w / 2.0
        self._slider_rect = (track_x, slider_y, track_w, track_h)

        arcade.draw_lbwh_rectangle_filled(track_x, slider_y, track_w, track_h, _SLIDER_TRACK)
        filled = fraction * track_w
        if filled > 0:
            arcade.draw_lbwh_rectangle_filled(track_x, slider_y, filled, track_h, _SLIDER_TRACK_FILLED)
        arcade.draw_lbwh_rectangle_filled(thumb_x, slider_y, thumb_w, track_h, _SLIDER_THUMB)
        arcade.draw_lbwh_rectangle_outline(
            thumb_x, slider_y, thumb_w, track_h, _SLIDER_THUMB_EDGE, 1,
        )
        self._text.draw(
            f"Speed {scale:.2f}x   (drag to change)",
            left + 12, slider_y + 18,     # label above the track, below the last key
            _MUTED, font_size=10,
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
        elif state == GameState.END:
            self.draw_end_screen(self.session)
        # pyglet's Window.draw() calls flip() (glXSwapBuffers) after on_draw.

    def on_resize(self, width: int, height: int) -> None:
        super().on_resize(width, height)
        self._layout_size = None
        self._recompute_layout()

    def _slider_hit(self, sx: float, sy: float) -> bool:
        if self._slider_rect is None:
            return False
        lx, ly, lw, lh = self._slider_rect
        scale = self.session.clock.time_scale
        fraction = (scale - _TIME_SCALE_MIN) / max(1e-6, _TIME_SCALE_MAX - _TIME_SCALE_MIN)
        fraction = max(0.0, min(1.0, fraction))
        thumb_w = 10
        thumb_x = lx + fraction * lw - thumb_w / 2.0
        thumb_rect = (thumb_x, ly - 2, thumb_w, lh + 4)
        return _point_in_rect(sx, sy, (lx, ly, lw, lh)) or _point_in_rect(sx, sy, thumb_rect)

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
