"""Physical screen representation using Arcade.

Reads a read-only snapshot of GameSession and draws state-specific screens.
Never mutates domain state.

Layout
------
* Left: a full-height sidebar with stacked information boxes (time, day,
  season, environment, inspector, controls).
* Right: the world, using the full height of the window.
* All colours come from the environment strategies (season palette, sky
  palette); the view only owns neutral UI chrome.

The world grid is `world.cell_size` world units; the view applies one uniform
world -> screen scale, so cells are never assumed to be a pixel size.
"""

import math

import arcade

from sim.components import GameSession, GameState
from sim.domain.visuals import SeasonPalette, SkyPalette

# --- UI chrome (not environmental colours) ---------------------------------
_TEXT = (238, 240, 245)
_MUTED = (168, 176, 190)
_DIM = (120, 128, 142)
_PANEL_BG = (8, 12, 20, 210)
_PANEL_BORDER = (255, 255, 255, 42)
_ACCENT = (120, 230, 150)
_INSPECT = (255, 120, 110)
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


def _mix(a, b, t: float):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _shade(color, factor: float):
    return tuple(max(0, min(255, int(round(c * factor)))) for c in color[:3])


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

        world = session.world
        self._world_width = world.width if world is not None else 1200.0
        self._world_height = world.height if world is not None else 800.0
        self._cell_size = world.cell_size if world is not None else 50.0

        self._scale = 1.0
        self._left = 0.0
        self._bottom = 0.0
        self._right = self._world_width
        self._top = self._world_height

        self._hover_world = None
        self._selected_world = None
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

    def _reading(self, session: GameSession):
        """World position used for the 'environment' box."""
        if self._selected_world is not None:
            return self._selected_world, "SELECTED"
        if self._hover_world is not None:
            return self._hover_world, "CURSOR"
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
        self.draw_playing(session)
        arcade.draw_lbwh_rectangle_filled(0, 0, self.width, self.height, (0, 0, 0, 150))
        arcade.draw_text(
            "PAUSED", self.width / 2, self.height / 2 + 18, _TEXT,
            font_size=44, anchor_x="center", anchor_y="center", bold=True,
        )
        arcade.draw_text(
            "P to resume   ·   Esc or Q to quit", self.width / 2,
            self.height / 2 - 28, _MUTED, font_size=15,
            anchor_x="center", anchor_y="center",
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
        return max(_SIDEBAR_MIN, min(_SIDEBAR_MAX, self.width * 0.30))

    def _recompute_layout(self) -> None:
        sidebar = self._sidebar_width()
        area_left = sidebar + 2 * _MARGIN
        area_bottom = _MARGIN
        area_w = max(1.0, self.width - area_left - _MARGIN)
        area_h = max(1.0, self.height - 2 * _MARGIN)

        self._scale = min(area_w / self._world_width, area_h / self._world_height)
        drawn_w = self._world_width * self._scale
        drawn_h = self._world_height * self._scale
        self._left = area_left + (area_w - drawn_w) / 2
        self._bottom = area_bottom + (area_h - drawn_h) / 2
        self._right = self._left + drawn_w
        self._top = self._bottom + drawn_h

    def _screen_to_world(self, sx: float, sy: float):
        if self._scale <= 0:
            return None
        wx = (sx - self._left) / self._scale
        wy = (sy - self._bottom) / self._scale
        if 0.0 <= wx <= self._world_width and 0.0 <= wy <= self._world_height:
            return wx, wy
        return None

    def _world_to_screen(self, wx: float, wy: float):
        return (self._left + wx * self._scale, self._bottom + wy * self._scale)

    # ------------------------------------------------------------------
    # Backdrop (start / end screens)
    # ------------------------------------------------------------------
    def _draw_backdrop(self, session: GameSession) -> None:
        env = session.environment
        light = env.light_level if env is not None else 0.7
        palette = self._sky()

        if light < 0.45:
            visibility = (0.45 - light) / 0.45
            color = _mix(palette.night, palette.star, 0.85 * visibility)
            for i in range(90):
                x = (i * 97.13) % self.width
                y = (i * 53.71) % self.height
                radius = 1.6 if i % 7 == 0 else 1.0
                arcade.draw_circle_filled(x, y, radius, color)

        celestial = self._celestial(session)
        if celestial is None:
            return

        cx = self.width * 0.5
        span = self.width * 0.42
        if celestial.sun_visible:
            x = cx - span / 2 + span * celestial.sun_progress
            y = self.height - 90 - 40 * math.sin(math.pi * celestial.sun_progress)
            arcade.draw_circle_filled(x, y, 16, palette.sun)
        elif celestial.moon_visible:
            x = cx - span / 2 + span * celestial.moon_progress
            y = self.height - 90 - 40 * math.sin(math.pi * celestial.moon_progress)
            arcade.draw_circle_filled(x, y, 13, palette.moon)
            offset = 5 + 8 * (1.0 - celestial.moon_illumination)
            arcade.draw_circle_filled(x + offset, y + 3, 12, _shade(self._sky_color(session), 1.0))

    def _draw_title_panel(
        self, title: str, subtitle: str, hint: str | None = None, accent=_ACCENT
    ) -> None:
        panel_w = min(620, self.width - 60)
        panel_h = 250
        left = (self.width - panel_w) / 2
        bottom = (self.height - panel_h) / 2
        self._panel(left, bottom, panel_w, panel_h)

        arcade.draw_text(
            title, self.width / 2, bottom + panel_h - 66, accent,
            font_size=44, anchor_x="center", anchor_y="center", bold=True,
        )
        arcade.draw_text(
            subtitle, self.width / 2, bottom + panel_h - 116, _TEXT,
            font_size=19, anchor_x="center", anchor_y="center",
        )
        arcade.draw_text(
            hint or "Esc: quit   ·   P: pause   ·   Click the world to inspect a cell",
            self.width / 2, bottom + 62, _MUTED, font_size=13,
            anchor_x="center", anchor_y="center",
        )

    # ------------------------------------------------------------------
    # World rendering
    # ------------------------------------------------------------------
    def _draw_world(self, session: GameSession) -> None:
        palette = self._palette()
        env = session.environment
        ambient = self._ambient(session)
        base = _shade(palette.ground, 0.32 + 0.68 * ambient)

        arcade.draw_lbwh_rectangle_filled(
            self._left, self._bottom,
            self._right - self._left, self._top - self._bottom,
            base,
        )

        if env is not None:
            self._draw_weather_cells(session, palette, ambient)
            self._draw_details(session, palette, ambient)
            self._draw_precipitation(session)

        self._draw_grid(session)
        self._draw_selection(session)

    def _draw_weather_cells(self, session: GameSession, palette, ambient: float) -> None:
        env = session.environment
        if env is None:
            return
        world = session.world
        cols = world.cols if world is not None else 1
        rows = world.rows if world is not None else 1
        cell = self._cell_size * self._scale
        if cell < 2:
            return

        for col in range(cols):
            for row in range(rows):
                wx, wy = self._world_to_screen(
                    (col + 0.5) * self._cell_size, (row + 0.5) * self._cell_size
                )
                tint = _WEATHER_TINT.get(env.weather_at(
                    (col + 0.5) * self._cell_size, (row + 0.5) * self._cell_size
                ))
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
        env = session.environment
        world = session.world
        if env is None or world is None:
            return

        tick = env.tick
        cell = self._cell_size * self._scale
        if cell < 3:
            return

        for col in range(world.cols):
            for row in range(world.rows):
                cx = (col + 0.5) * self._cell_size
                cy = (row + 0.5) * self._cell_size
                condition = env.weather_at(cx, cy)
                if condition not in ("rain", "storm", "snow"):
                    continue

                left = self._left + col * cell
                bottom = self._bottom + row * cell
                count = 5 if condition == "storm" else 3
                speed = 3.4 if condition == "storm" else 2.2

                for i in range(count):
                    px = left + ((i * 37.0 + col * 13.0) % max(1.0, cell))
                    py = bottom + ((tick * speed + i * 41.0 + row * 17.0) % max(1.0, cell))
                    if condition == "snow":
                        arcade.draw_circle_filled(px, py, 1.6, (240, 246, 255, 210))
                    else:
                        arcade.draw_line(
                            px, py, px - 2, py - 8, (170, 200, 240, 160), 1
                        )

    def _draw_grid(self, session: GameSession) -> None:
        step = self._cell_size * self._scale
        if step < 6:
            return
        color = _shade(self._palette().ground, 0.55)

        col = 1
        while col * self._cell_size < self._world_width:
            sx, _ = self._world_to_screen(col * self._cell_size, 0.0)
            arcade.draw_line(sx, self._bottom, sx, self._top, (*color, 90), 1)
            col += 1
        row = 1
        while row * self._cell_size < self._world_height:
            _, sy = self._world_to_screen(0.0, row * self._cell_size)
            arcade.draw_line(self._left, sy, self._right, sy, (*color, 90), 1)
            row += 1

        arcade.draw_lbwh_rectangle_outline(
            self._left, self._bottom,
            self._right - self._left, self._top - self._bottom,
            (245, 246, 250, 170), 2,
        )

    def _draw_selection(self, session: GameSession) -> None:
        if self._selected_world is not None:
            self._draw_cell_marker(self._selected_world, _INSPECT, 2)
            sx, sy = self._world_to_screen(*self._selected_world)
            arcade.draw_line(sx - 6, sy, sx + 6, sy, _INSPECT, 1)
            arcade.draw_line(sx, sy - 6, sx, sy + 6, _INSPECT, 1)
        if self._hover_world is not None:
            self._draw_cell_marker(self._hover_world, (255, 255, 255, 90), 1)

    def _draw_cell_marker(self, world_xy, color, width: float) -> None:
        col = int(world_xy[0] // self._cell_size)
        row = int(world_xy[1] // self._cell_size)
        left = self._left + col * self._cell_size * self._scale
        bottom = self._bottom + row * self._cell_size * self._scale
        size = self._cell_size * self._scale
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
        arcade.draw_text(
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
        world = session.world
        env = session.environment
        calendar = env.calendar if env is not None else None
        palette = self._palette()

        left = _MARGIN
        width = self._sidebar_width() - _MARGIN
        controls_h = 96
        limit = _MARGIN + controls_h + _GAP
        cursor = self.height - _MARGIN

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
            arcade.draw_text(
                f"Day {day}   ·   {clock}", left + 12, top - 40, _TEXT,
                font_size=17, bold=True,
            )
            arcade.draw_text(
                f"Year {year}   ·   tick {tick}   ·   sim {self._format_sim_time(tick)}",
                left + 12, top - 62, _MUTED, font_size=11,
            )
            arcade.draw_text(
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
            arcade.draw_text(
                f"light {light:.0%}", left + width - 76, top - 16, _MUTED, font_size=11,
            )
            self._bar(left + 12, top - 34, width - 24, 6, fraction, _SUN)
            arcade.draw_text("00", left + 12, top - 50, _DIM, font_size=9)
            arcade.draw_text("12", left + width / 2 - 4, top - 50, _DIM, font_size=9)
            arcade.draw_text("24", left + width - 24, top - 50, _DIM, font_size=9)
            self._draw_sun_track(session, left + 12, top - 84, width - 24, 22)

        # ---- Season (independent of the day bar) ----------------------
        h = 84
        slot = take(h)
        if slot is not None:
            top, bottom = slot
            self._box(left, top, width, h, "Season")
            arcade.draw_text(
                palette.name, left + 12, top - 38, _TEXT, font_size=18, bold=True,
            )
            if calendar is not None:
                info = (f"day {calendar.day_of_season} of {calendar.days_per_season}"
                        f"   ·   year {calendar.year}")
            else:
                info = "static"
            arcade.draw_text(info, left + 12, top - 58, _MUTED, font_size=11)
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
                arcade.draw_text(
                    f"{label}   {env.light_at(target[0], target[1]):.0%} light"
                    f"   ·   {condition}",
                    left + 12, top - 38, _WEATHER_LABEL.get(condition, _TEXT),
                    font_size=13,
                )
                arcade.draw_text(
                    f"{env.temperature_at(target[0], target[1]):.1f} °C"
                    f"    {env.humidity_at(target[0], target[1]):.0%} RH"
                    f"    {env.pressure_at(target[0], target[1]):.0f} hPa",
                    left + 12, top - 62, _TEXT, font_size=13,
                )
                arcade.draw_text(
                    f"climate: {palette.base_temperature:.0f} ± "
                    f"{palette.temperature_swing:.0f} °C   ·   {palette.name}",
                    left + 12, top - 84, _MUTED, font_size=11,
                )
            else:
                arcade.draw_text(
                    "no environment", left + 12, top - 42, _MUTED, font_size=13,
                )
            arcade.draw_text(
                "click a cell to pin it", left + 12, top - 108, _DIM, font_size=10,
            )

        # ---- Inspector ------------------------------------------------
        h = 116
        slot = take(h)
        if slot is not None:
            top, bottom = slot
            self._box(left, top, width, h, "Inspector")
            if self._selected_world is not None and env is not None:
                wx, wy = self._selected_world
                col, row = world.cell_index(wx, wy) if world is not None else (0, 0)
                condition = env.weather_at(wx, wy)
                arcade.draw_text(
                    f"cell ({col}, {row})   ·   x {wx:.0f}  y {wy:.0f}",
                    left + 12, top - 38, _MUTED, font_size=11,
                )
                arcade.draw_text(
                    f"{env.temperature_at(wx, wy):.1f} °C", left + 12, top - 68,
                    _TEXT, font_size=24, bold=True,
                )
                arcade.draw_text(
                    f"{env.humidity_at(wx, wy):.0%} RH   ·   "
                    f"{env.pressure_at(wx, wy):.0f} hPa   ·   "
                    f"{env.light_at(wx, wy):.0%} light",
                    left + 12, top - 90, _TEXT, font_size=11,
                )
                arcade.draw_text(
                    condition, left + width - 80, top - 68,
                    _WEATHER_LABEL.get(condition, _TEXT), font_size=13,
                )
            else:
                arcade.draw_text(
                    "Click any cell in the world", left + 12, top - 44,
                    _TEXT, font_size=13,
                )
                arcade.draw_text(
                    "to read its temperature, light,", left + 12, top - 64,
                    _MUTED, font_size=11,
                )
                arcade.draw_text(
                    "humidity and pressure.", left + 12, top - 82,
                    _MUTED, font_size=11,
                )

        # ---- Weather field (fills the remaining stack) -----------------
        remaining = cursor - limit
        if remaining >= 76 and env is not None and world is not None:
            top = cursor
            h = remaining
            self._box(left, top, width, h, "Weather field")
            self._draw_weather_census(session, left + 12, top - 34, width - 24)

        # ---- Controls (anchored to the bottom of the sidebar) ---------
        h = controls_h
        self._box(left, _MARGIN + h, width, h, "Controls")
        lines = [
            ("SPACE", "start / restart"),
            ("P", "pause / resume"),
            ("Esc / Q", "quit"),
            ("Click", "inspect cell"),
        ]
        y = _MARGIN + h - 40
        for key, action in lines:
            arcade.draw_text(key, left + 12, y, _ACCENT, font_size=11, bold=True)
            arcade.draw_text(action, left + 96, y, _MUTED, font_size=11)
            y -= 17

    def _draw_weather_census(self, session: GameSession, left: float, top: float,
                             width: float) -> None:
        """How many cells show each condition: proves the field is not uniform."""
        env = session.environment
        world = session.world
        if env is None or world is None:
            return

        counts = {name: 0 for name in _WEATHER_LABEL}
        total = world.cols * world.rows
        
        # Use weather strategy if available, otherwise skip this section
        weather_strategy = env.weather_strategy
        if weather_strategy is None:
            return
            
        for col in range(world.cols):
            for row in range(world.rows):
                condition = weather_strategy.weather_at_cell(col, row)
                counts[condition] = counts.get(condition, 0) + 1

        y = top
        for condition, count in counts.items():
            if count == 0:
                continue
            color = _WEATHER_LABEL.get(condition, _TEXT)
            arcade.draw_lbwh_rectangle_filled(left, y - 1, 8, 8, color)
            arcade.draw_text(
                f"{condition}", left + 16, y, _TEXT, font_size=11,
            )
            arcade.draw_text(
                f"{count:>3} cells   ·   {count / total:>4.0%}",
                left + width - 92, y, _MUTED, font_size=11,
            )
            y -= 17

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
        state = self.session.state
        if state in (GameState.START, GameState.END):
            self._selected_world = None
            self._hover_world = None
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
        self._recompute_layout()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> None:
        if self.session.state in (GameState.PLAYING, GameState.PAUSED):
            self._hover_world = self._screen_to_world(x, y)
        else:
            self._hover_world = None

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> None:
        if self.session.state not in (GameState.PLAYING, GameState.PAUSED):
            return
        world = self._screen_to_world(x, y)
        if world is not None:
            self._selected_world = world
        elif button == 1:
            self._selected_world = None


def _season_color(palette: SeasonPalette, ambient: float):
    """Readable text colour derived from the season ground colour."""
    return _mix(_shade(palette.ground, 0.6 + 0.4 * ambient), (255, 255, 255), 0.45)
