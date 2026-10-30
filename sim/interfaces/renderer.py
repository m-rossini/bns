"""Interface for the physical screen representation.

Uses typing.Protocol (structural subtyping) to avoid ABC metaclass
conflicts with arcade.Window.
"""

from typing import Protocol, runtime_checkable

from sim.components import GameSession


@runtime_checkable
class IRenderer(Protocol):
    def draw_start_screen(self) -> None: ...
    def draw_playing(self, session: GameSession) -> None: ...
    def draw_paused(self, session: GameSession) -> None: ...
    def draw_end_screen(self, session: GameSession) -> None: ...
    def flip(self) -> None: ...
