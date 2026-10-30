"""Physical screen representation using Arcade.

Reads a read-only snapshot of GameSession and draws state-specific screens.
Never mutates domain state. Visualises the day/night cycle, seasons, weather,
and a temperature inspector driven by mouse clicks.
"""

import math

import arcade

from sim.components import GameSession, GameState

# --- Palette ---------------------------------------------------------------

_NIGHT_SKY = (10, 14, 32)
_DAY_SKY = (122, 182, 228)
_TWILIGHT_SKY = (232, 138, 84)
_OVERCAST = (92, 98, 110)

_GROUND = {
    "spring": (96, 170, 88),
    "summer": (68, 146, 72),
    "autumn": (178, 128, 62),
    "winter": (222, 230, 236),
}

_WEATHER_TEXT = {
    "clear": (255, 226, 140),
    "cloudy": (200, 205, 215),
    "rain": (165, 205, 255),
    "storm": (185, 165, 250),
    "snow": (235, 245, 255),
}

# Seasonal ground speckles (grass, flowers, leaves, snow patches).
_GROUND_DETAIL = {
    "spring": [(250, 246, 180), (248, 186, 214), (232, 248, 236)],
    "summer": [(52, 122, 58), (92, 168, 84), (38, 110, 54)],
    "autumn": [(214, 124, 52), (166, 92, 42), (206, 168, 70)],
    "winter": [(246, 250, 255), (206, 222, 238), (232, 240, 248)],
}

_TEXT = (238, 240, 245)
_MUTED = (168, 176, 190)
_PANEL_BG = (8, 12, 20, 200)
_PANEL_BORDER = (255, 255, 255, 55)
_ACCENT = (120, 230, 150)
_INSPECT = (255, 120, 110)


def _mix(a, b, t: float):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _shade(color, factor: float):
    return tuple(max(0, min(255, int(c * factor))) for c in color[:3])


class ArcadeView(arcade.Window):  # implements IRenderer structurally
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

        self._world_width = session.world.width if session.world else 1200.0
        self._world_height = session.world.height if session.world else 800.0
        self._scale = 1.0
        self._left = 0.0
        self._bottom = 0.0
        self._right = self._world_width
        self._top = self._world_height

        self._hover_world = None
        self._selected_world = None
        self._recompute_layout()

    # ------------------------------------------------------------------
    # IRenderer implementation
    # ------------------------------------------------------------------
    def draw_start_screen(self) -> None:
        self._draw_sky()
        self._draw_stars()
        self._draw_sun_moon()

        panel_w, panel_h = min(620, self.width - 40), 250
        left = (self.width - panel_w) / 2
        bottom = (self.height - panel_h) / 2
        self._panel(left, bottom, panel_w, panel_h)

        cx = self.width / 2
        arcade.draw_text(
            "BEAN WORLD",
            cx,
            bottom + panel_h - 62,
            _ACCENT,
            font_size=46,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )
        arcade.draw_text(
            "A pause-aware bean simulation",
            cx,
            bottom + panel_h - 108,
            _MUTED,
            font_size=16,
            anchor_x="center",
            anchor_y="center",
        )
        arcade.draw_text(
            "Press SPACE to start",
            cx,
            bottom + 78,
            _TEXT,
            font_size=22,
            anchor_x="center",
            anchor_y="center",
        )
        arcade.draw_text(
            "Esc: quit    ·    P: pause    ·    Click the world: inspect temperature",
            cx,
            bottom + 38,
            _MUTED,
            font_size=13,
            anchor_x="center",
            anchor_y="center",
        )

    def draw_playing(self, session: GameSession) -> None:
        self._draw_sky()
        self._draw_stars()
        self._draw_sun_moon()
        self._draw_ground()
        self._draw_ground_detail()
        self._draw_grid()
        self._draw_barriers(session.world)
        self._draw_weather(session)
        self._draw_selection(session)
        self._draw_panels(session)

    def draw_paused(self, session: GameSession) -> None:
        self.draw_playing(session)
        arcade.draw_lbwh_rectangle_filled(
            0, 0, self.width, self.height, (0, 0, 0, 150)
        )
        cx = self.width / 2
        arcade.draw_text(
            "PAUSED",
            cx,
            self.height / 2 + 24,
            _TEXT,
            font_size=46,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )
        arcade.draw_text(
            "P or Esc to resume    ·    Q to quit",
            cx,
            self.height / 2 - 26,
            _MUTED,
            font_size=16,
            anchor_x="center",
            anchor_y="center",
        )

    def draw_end_screen(self, session: GameSession) -> None:
        self.clear((26, 12, 16))
        cx = self.width / 2
        arcade.draw_text(
            "GAME OVER",
            cx,
            self.height / 2 + 70,
            (240, 96, 96),
            font_size=48,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )
        arcade.draw_text(
            f"Reason: {session.end_reason or 'ended'}",
            cx,
            self.height / 2 + 14,
            _TEXT,
            font_size=20,
            anchor_x="center",
            anchor_y="center",
        )
        arcade.draw_text(
            f"Ticks survived: {session.clock.tick}"
            f"    ·    Sim time: {self._format_sim_time(session.clock.tick)}",
            cx,
            self.height / 2 - 20,
            _MUTED,
            font_size=16,
            anchor_x="center",
            anchor_y="center",
        )
        arcade.draw_text(
            "Press SPACE to restart",
            cx,
            self.height / 2 - 76,
            _TEXT,
            font_size=18,
            anchor_x="center",
            anchor_y="center",
        )

    # NOTE: `flip()` is intentionally inherited from pyglet's Window. It calls
    # glXSwapBuffers, which is what makes the back buffer visible. Overriding it
    # with a no-op leaves the window showing a stale (black) front buffer.

    # ------------------------------------------------------------------
    # Layout / world <-> screen mapping
    # ------------------------------------------------------------------
    def _recompute_layout(self) -> None:
        pad = 18.0
        top_band = 112.0
        avail_w = max(1.0, self.width - 2 * pad)
        avail_h = max(1.0, self.height - 2 * pad - top_band)
        self._scale = min(
            avail_w / self._world_width, avail_h / self._world_height
        )
        drawn_w = self._world_width * self._scale
        drawn_h = self._world_height * self._scale
        self._left = (self.width - drawn_w) / 2
        self._bottom = pad + (avail_h - drawn_h) / 2
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
        return (
            self._left + wx * self._scale,
            self._bottom + wy * self._scale,
        )

    # ------------------------------------------------------------------
    # Visual helpers
    # ------------------------------------------------------------------
    def _environment(self, session: GameSession):
        return session.environment

    def _light(self, session: GameSession) -> float:
        env = self._environment(session)
        return env.light_level if env is not None else 0.7

    def _season(self, session: GameSession) -> str:
        env = self._environment(session)
        return env.season if env is not None else "spring"

    def _phase(self, session: GameSession) -> str:
        env = self._environment(session)
        return env.phase if env is not None else "day"

    def _weather(self, session: GameSession) -> str:
        env = self._environment(session)
        return env.weather if env is not None else "clear"

    def _ambient(self, session: GameSession) -> float:
        """Light after weather dimming, used to shade the world."""
        light = self._light(session)
        weather = self._weather(session)
        dim = {"clear": 1.0, "cloudy": 0.82, "rain": 0.68,
               "storm": 0.5, "snow": 0.85}.get(weather, 1.0)
        return max(0.0, min(1.0, light * dim))

    def _sky_color(self, session: GameSession):
        light = self._light(session)
        weather = self._weather(session)
        phase = self._phase(session)

        sky = _mix(_NIGHT_SKY, _DAY_SKY, light)
        if phase in ("dawn", "dusk"):
            strength = max(0.0, 1.0 - abs(light - 0.28) / 0.28)
            sky = _mix(sky, _TWILIGHT_SKY, 0.55 * strength)

        if weather == "cloudy":
            sky = _mix(sky, _OVERCAST, 0.35)
        elif weather == "rain":
            sky = _mix(sky, _OVERCAST, 0.55)
        elif weather == "storm":
            sky = _mix(sky, (58, 60, 78), 0.7)
        elif weather == "snow":
            sky = _mix(sky, (196, 204, 216), 0.5)
        return sky

    def _draw_sky(self) -> None:
        self.clear(self._sky_color(self.session))

    def _draw_stars(self) -> None:
        light = self._light(self.session)
        if light >= 0.45:
            return
        visibility = (0.45 - light) / 0.45
        color = _mix(_NIGHT_SKY, (235, 240, 255), 0.85 * visibility)
        width, height = float(self.width), float(self.height)
        for i in range(80):
            x = (i * 97.13) % width
            y = (i * 53.71) % height
            radius = 1.6 if i % 7 == 0 else 1.0
            arcade.draw_circle_filled(x, y, radius, color)

    def _draw_sun_moon(self) -> None:
        env = self._environment(self.session)
        dn = env.daynight_strategy if env is not None else None
        if dn is None:
            return
        ticks_per_day = dn.ticks_per_day
        progress = (self.session.clock.tick % ticks_per_day) / ticks_per_day

        band_bottom = self._top
        band_top = float(self.height) - 8.0
        span = max(10.0, band_top - band_bottom)

        # Keep the arc in the gap between the two HUD panels.
        arc_left = min(float(self.width) - 2.0, 436.0)
        arc_right = max(arc_left + 1.0, float(self.width) - 360.0)
        arc_width = max(1.0, arc_right - arc_left)

        if 0.25 <= progress <= 0.75:
            t = (progress - 0.25) / 0.5
            x = arc_left + arc_width * t
            y = band_bottom + 22.0 + span * 0.35 * (0.3 + 0.7 * math.sin(math.pi * t))
            arcade.draw_circle_filled(x, y, 17, (255, 228, 130))
            arcade.draw_circle_outline(x, y, 24, (255, 210, 110, 90), 2)
        else:
            t = ((progress + 0.25) % 1.0) / 0.5
            x = arc_left + arc_width * t
            y = band_bottom + 22.0 + span * 0.35 * (0.3 + 0.7 * math.sin(math.pi * t))
            arcade.draw_circle_filled(x, y, 14, (222, 228, 245))
            arcade.draw_circle_filled(
                x - 4, y + 3, 3, _shade((222, 228, 245), 0.82)
            )

    def _draw_ground(self) -> None:
        season = self._season(self.session)
        ambient = self._ambient(self.session)
        base = _GROUND.get(season, _GROUND["spring"])
        ground = _shade(base, 0.35 + 0.65 * ambient)

        arcade.draw_lbwh_rectangle_filled(
            self._left,
            self._bottom,
            self._right - self._left,
            self._top - self._bottom,
            ground,
        )

    def _draw_ground_detail(self) -> None:
        season = self._season(self.session)
        ambient = self._ambient(self.session)
        colors = _GROUND_DETAIL.get(season, _GROUND_DETAIL["spring"])
        factor = 0.4 + 0.6 * ambient

        for i in range(130):
            wx = (i * 97.31 + 17.0) % self._world_width
            wy = (i * 57.73 + 29.0) % self._world_height
            sx, sy = self._world_to_screen(wx, wy)
            radius = 1.4 + (i % 4) * 0.6
            arcade.draw_circle_filled(
                sx, sy, radius, _shade(colors[i % len(colors)], factor)
            )

    def _draw_grid(self) -> None:
        season = self._season(self.session)
        ambient = self._ambient(self.session)
        line_color = _shade(_GROUND.get(season, _GROUND["spring"]), 0.28 + 0.5 * ambient)
        step = 100.0
        x = step
        while x < self._world_width:
            sx, _ = self._world_to_screen(x, 0.0)
            arcade.draw_line(
                sx, self._bottom, sx, self._top, line_color, 1
            )
            x += step
        y = step
        while y < self._world_height:
            _, sy = self._world_to_screen(0.0, y)
            arcade.draw_line(
                self._left, sy, self._right, sy, line_color, 1
            )
            y += step

        arcade.draw_lbwh_rectangle_outline(
            self._left,
            self._bottom,
            self._right - self._left,
            self._top - self._bottom,
            (245, 246, 250, 170),
            2,
        )

    def _draw_barriers(self, world) -> None:
        if world is None:
            return
        ambient = self._ambient(self.session)
        factor = 0.45 + 0.55 * ambient
        fill = _shade((118, 120, 130), factor)
        outline = _shade((52, 54, 62), max(0.6, factor))

        for barrier in world.barriers:
            sx, sy = self._world_to_screen(barrier.x, barrier.y)
            if barrier.kind == "rect":
                half_w = barrier.width * self._scale / 2
                half_h = barrier.height * self._scale / 2
                arcade.draw_lbwh_rectangle_filled(
                    sx - half_w, sy - half_h, half_w * 2, half_h * 2, fill
                )
                arcade.draw_lbwh_rectangle_outline(
                    sx - half_w, sy - half_h, half_w * 2, half_h * 2,
                    outline, 2,
                )
            elif barrier.kind == "circle":
                radius = barrier.radius * self._scale
                arcade.draw_circle_filled(sx, sy, radius, fill)
                arcade.draw_circle_outline(sx, sy, radius, outline, 2)

    def _draw_weather(self, session: GameSession) -> None:
        weather = self._weather(session)
        if weather not in ("rain", "storm", "snow"):
            return

        tick = session.environment.tick if session.environment else session.clock.tick
        area_w = self._right - self._left
        area_h = self._top - self._bottom
        count = 170 if weather == "storm" else 95
        is_snow = weather == "snow"

        for i in range(count):
            speed = 2.6 + (i % 5) * 0.7
            x = self._left + ((i * 137.0 + 43.0) % area_w)
            y = self._bottom + ((area_h - (tick * speed + i * 37.0) % area_h))
            if is_snow:
                arcade.draw_circle_filled(x, y, 2.0, (240, 246, 255, 210))
            else:
                arcade.draw_line(
                    x, y, x - 3, y - 11, (170, 200, 240, 150), 1
                )

    def _draw_selection(self, session: GameSession) -> None:
        env = self._environment(session)
        if self._selected_world is not None and env is not None:
            wx, wy = self._selected_world
            sx, sy = self._world_to_screen(wx, wy)
            arcade.draw_circle_outline(sx, sy, 9, _INSPECT, 2)
            arcade.draw_line(sx - 15, sy, sx + 15, sy, _INSPECT, 1)
            arcade.draw_line(sx, sy - 15, sx, sy + 15, _INSPECT, 1)

        elif self._hover_world is not None and env is not None:
            wx, wy = self._hover_world
            sx, sy = self._world_to_screen(wx, wy)
            arcade.draw_circle_outline(sx, sy, 6, (255, 255, 255, 90), 1)

    # ------------------------------------------------------------------
    # Panels / text
    # ------------------------------------------------------------------
    def _panel(self, left: float, bottom: float, width: float, height: float):
        arcade.draw_lbwh_rectangle_filled(
            left, bottom, width, height, _PANEL_BG
        )
        arcade.draw_lbwh_rectangle_outline(
            left, bottom, width, height, _PANEL_BORDER, 1
        )

    def _bar(
        self,
        left: float,
        bottom: float,
        width: float,
        height: float,
        fraction: float,
        color,
    ) -> None:
        arcade.draw_lbwh_rectangle_filled(
            left, bottom, width, height, (38, 44, 56, 220)
        )
        filled = max(0.0, min(1.0, fraction)) * width
        if filled > 0:
            arcade.draw_lbwh_rectangle_filled(
                left, bottom, filled, height, color
            )

    def _draw_panels(self, session: GameSession) -> None:
        env = session.environment
        tick = session.clock.tick

        # --- Time & weather panel (top-left) ---
        px, py, pw, ph = 16.0, self.height - 148.0, 404.0, 132.0
        self._panel(px, py, pw, ph)

        arcade.draw_text(
            "TIME & WEATHER", px + 14, py + ph - 20, _MUTED,
            font_size=11, bold=True, anchor_y="baseline",
        )
        arcade.draw_text(
            f"Tick {tick}    ·    sim {self._format_sim_time(tick)}",
            px + 14, py + ph - 44, _TEXT, font_size=15,
        )

        day_text, clock_text, day_progress = self._day_info(session)
        arcade.draw_text(
            f"{day_text}    ·    {clock_text}    ·    {self._phase(session)}",
            px + 14, py + ph - 66, _TEXT, font_size=14,
        )
        weather = self._weather(session)
        arcade.draw_text(
            f"{self._season(session).title()}    ·    light {self._light(session):.0%}"
            f"    ·    {weather}",
            px + 14, py + ph - 86,
            _WEATHER_TEXT.get(weather, _TEXT), font_size=14,
        )

        bar_x = px + 66
        bar_w = pw - 80
        arcade.draw_text(
            "day", px + 14, py + 19, _MUTED, font_size=10,
            anchor_y="center",
        )
        self._bar(bar_x, py + 16, bar_w, 5, day_progress, (255, 205, 120))
        arcade.draw_text(
            "season", px + 14, py + 7, _MUTED, font_size=10,
            anchor_y="center",
        )
        self._bar(
            bar_x, py + 5, bar_w, 4, self._season_progress(session),
            (140, 220, 150),
        )

        # --- Inspector panel (top-right) ---
        ix = self.width - 344.0
        iy = self.height - 148.0
        iw, ih = 328.0, 132.0
        self._panel(ix, iy, iw, ih)
        arcade.draw_text(
            "TEMPERATURE INSPECTOR", ix + 14, iy + ih - 20, _MUTED,
            font_size=11, bold=True,
        )

        target = self._selected_world or self._hover_world
        if target is None:
            arcade.draw_text(
                "Click anywhere in the arena",
                ix + 14, iy + ih - 52, _TEXT, font_size=14,
            )
            arcade.draw_text(
                "to read its temperature.",
                ix + 14, iy + ih - 72, _MUTED, font_size=13,
            )
        else:
            wx, wy = target
            temp = (
                env.temperature_at(wx, wy) if env is not None else None
            )
            label = "SELECTED" if self._selected_world else "CURSOR"
            arcade.draw_text(
                f"{label}    x {wx:.0f}    y {wy:.0f}",
                ix + 14, iy + ih - 46, _MUTED, font_size=12,
            )
            arcade.draw_text(
                f"{temp:.1f} °C" if temp is not None else "—",
                ix + 14, iy + ih - 78, _TEXT, font_size=28, bold=True,
            )
            arcade.draw_text(
                f"{self._season(session)} · {self._phase(session)} · {weather}",
                ix + 14, iy + ih - 104,
                _WEATHER_TEXT.get(weather, _MUTED), font_size=12,
            )

        # --- Controls (bottom-left) ---
        arcade.draw_lbwh_rectangle_filled(
            16, 14, 470, 26, (8, 12, 20, 170)
        )
        arcade.draw_text(
            "SPACE start   ·   P/Esc pause   ·   Q quit   ·   click: inspect",
            26, 21, _MUTED, font_size=11,
        )

    def _format_sim_time(self, ticks: int) -> str:
        total = ticks / self._tick_rate
        minutes = int(total // 60)
        seconds = total % 60
        return f"{minutes:02d}:{seconds:04.1f}"

    def _day_info(self, session: GameSession):
        env = session.environment
        dn = env.daynight_strategy if env is not None else None
        if dn is None:
            return "Day —", "--:--", 0.0
        day_length = dn.ticks_per_day
        tick = session.clock.tick
        day = tick // day_length + 1
        fraction = (tick % day_length) / day_length
        hours = fraction * 24.0
        hh = int(hours)
        mm = int((hours - hh) * 60)
        return f"Day {day}", f"{hh:02d}:{mm:02d}", fraction

    def _season_progress(self, session: GameSession) -> float:
        env = session.environment
        season = env.season_strategy if env is not None else None
        if season is None:
            return 0.0
        length = season.ticks_per_season
        return (session.clock.tick % length) / length

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
