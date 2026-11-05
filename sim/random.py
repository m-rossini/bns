"""Central random number generation for the simulation.

Provides a single seeded `random.Random` instance used by all subsystems.
This ensures reproducible runs when a seed is provided, and allows
subsystems to share or isolate their random state as needed.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class RandomConfig:
    """Configuration for the global random number generator.

    If ``seed`` is None, the system entropy source is used (non-reproducible).
    If ``seed`` is an int, the generator is fully deterministic.
    """
    seed: Optional[int] = None


#: Module-level random instance. Initialized by `init_random()`.
_rng: Optional[random.Random] = None


def init_random(config: RandomConfig) -> random.Random:
    """Initialize the global random generator.

    Call once at startup (e.g., from the container). Returns the RNG instance.
    """
    global _rng
    if config.seed is None:
        _rng = random.Random()  # system entropy
    else:
        _rng = random.Random(config.seed)
    return _rng


def get_rng() -> random.Random:
    """Get the global random generator.

    Initializes with system entropy if not already initialized.
    """
    global _rng
    if _rng is None:
        _rng = random.Random()  # system entropy
    return _rng


def random_direction(rng: Optional[random.Random] = None) -> tuple[float, float]:
    """Return a random unit vector (uniform on the circle)."""
    if rng is None:
        rng = get_rng()
    angle = rng.random() * 2.0 * 3.141592653589793
    return (math.cos(angle), math.sin(angle))


def random_float(rng: Optional[random.Random] = None, a: float = 0.0, b: float = 1.0) -> float:
    """Uniform random float in [a, b)."""
    if rng is None:
        rng = get_rng()
    return rng.uniform(a, b)


def random_int(rng: Optional[random.Random] = None, a: int = 0, b: int = 1) -> int:
    """Uniform random int in [a, b]."""
    if rng is None:
        rng = get_rng()
    return rng.randint(a, b)


def random_choice(seq, rng: Optional[random.Random] = None):
    """Choose a random element from a non-empty sequence."""
    if rng is None:
        rng = get_rng()
    return rng.choice(seq)


def random_shuffle(seq, rng: Optional[random.Random] = None) -> None:
    """Shuffle a sequence in place."""
    if rng is None:
        rng = get_rng()
    rng.shuffle(seq)