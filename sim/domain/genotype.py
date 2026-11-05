"""Bean genotype (immutable traits set at birth) and phenotype (mutable state)."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from sim.config import GenotypeConfig
    from sim.domain.beans import Bean


@dataclass(frozen=True, slots=True)
class Genotype:
    """Immutable genetic traits determined at bean creation."""

    # Energy system
    energy_capacity: float        # Maximum energy this bean can store
    metabolic_rate: float         # Base energy consumption per tick (at rest)
    drag_coefficient: float       # Quadratic drag factor: cost = drag * speed²

    # Movement traits
    max_speed: float              # Maximum speed this bean can achieve
    acceleration: float           # Max speed change per tick (thrust/brake)

    # Visual
    base_color: Tuple[int, int, int]  # Color when healthy
    dormant_color: Tuple[int, int, int] = (139, 69, 19)  # Brown when energy=0


@dataclass(slots=True)
class Phenotype:
    """Mutable state that changes during simulation."""

    # Energy state
    current_energy: float         # Current energy level (0 to energy_capacity)

    # Movement state
    current_speed: float          # Current speed magnitude
    velocity: Tuple[float, float]  # Current velocity vector (vx, vy)

    # Life state
    age: int = 0                  # Ticks alive
    is_dormant: bool = False      # True when energy <= 0

    # Visual state
    color: Tuple[int, int, int] = field(init=False)

    def __post_init__(self):
        self.color = self._compute_color()

    def _compute_color(self) -> Tuple[int, int, int]:
        # Will be overridden by genotype reference
        return (255, 255, 255)

    def update_color(self, genotype: Genotype) -> None:
        """Update color based on energy state and genotype."""
        if self.is_dormant:
            self.color = genotype.dormant_color
        else:
            self.color = genotype.base_color


@dataclass(frozen=True, slots=True)
class BeanGenotypePhenotype:
    """Combined genotype and phenotype for a bean."""
    genotype: Genotype
    phenotype: Phenotype


# ------------------------------------------------------------------
# Default genotype factory (for testing/config)
# ------------------------------------------------------------------

DEFAULT_GENOTYPE = Genotype(
    energy_capacity=1000.0,
    metabolic_rate=1.0,           # 1 energy/tick at rest
    drag_coefficient=0.01,        # 0.01 * speed² energy/tick
    max_speed=60.0,               # World units per second
    acceleration=30.0,            # Max speed change per second
    base_color=(0, 0, 255),       # Blue default
    dormant_color=(139, 69, 19),  # Brown
)


def create_default_phenotype(genotype: Genotype = DEFAULT_GENOTYPE) -> Phenotype:
    """Create a phenotype with default starting values."""
    return Phenotype(
        current_energy=genotype.energy_capacity,
        current_speed=0.0,
        velocity=(0.0, 0.0),
        age=0,
        is_dormant=False,
    )


def draw_genotype(
    rng: random.Random,
    ranges: "GenotypeConfig",
    base_color: Tuple[int, int, int],
    dormant_color: Tuple[int, int, int] = (139, 69, 19),
) -> Genotype:
    """Draw a random Genotype from ``GenotypeConfig`` ranges.

    Each numeric gene is drawn uniformly from its configured (min, max)
    range, so the initial population has genetic variety while staying
    within sane bounds. ``base_color`` comes from the gender controller.
    """
    return Genotype(
        energy_capacity=rng.uniform(*ranges.energy_capacity),
        metabolic_rate=rng.uniform(*ranges.metabolic_rate),
        drag_coefficient=rng.uniform(*ranges.drag_coefficient),
        max_speed=rng.uniform(*ranges.max_speed),
        acceleration=rng.uniform(*ranges.acceleration),
        base_color=base_color,
        dormant_color=dormant_color,
    )


def apply_energy_cost(
    phenotype: Phenotype,
    genotype: Genotype,
    dt: float,
    speed: float,
    acceleration: float = 0.0,
) -> float:
    """
    Calculate and apply energy cost for movement.

    Returns the energy consumed this tick.
    """
    # Base metabolic cost (always paid)
    metabolic_cost = genotype.metabolic_rate * dt

    # Quadratic drag cost: drag_coefficient * speed²
    drag_cost = genotype.drag_coefficient * (speed ** 2) * dt

    # Acceleration/deceleration cost: extra energy for changing speed
    accel_cost = abs(acceleration) * dt * 0.5  # Tunable factor

    total_cost = metabolic_cost + drag_cost + accel_cost

    phenotype.current_energy = max(0.0, phenotype.current_energy - total_cost)

    # Check for dormancy
    if phenotype.current_energy <= 0.0:
        phenotype.is_dormant = True
        phenotype.current_energy = 0.0
        phenotype.current_speed = 0.0
        phenotype.velocity = (0.0, 0.0)

    return total_cost


def apply_energy_gain(
    phenotype: Phenotype,
    genotype: Genotype,
    energy_gain: float,
) -> None:
    """Apply energy gain (from environment/food)."""
    phenotype.current_energy = min(genotype.energy_capacity, phenotype.current_energy + energy_gain)

    # Wake up from dormancy if energy recovered
    if phenotype.is_dormant and phenotype.current_energy > 0.0:
        phenotype.is_dormant = False

    phenotype.update_color(genotype)