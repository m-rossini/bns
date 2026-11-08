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

    # Feeding: genotype baseline, modulated by the phenotype's condition.
    digestion_efficiency: float = 0.6
    #: Appetite: energy units the bean can take from one food contact.
    digestion_capacity: float = 80.0

    # Lifespan: an absolute tick cap inherited from the species ceiling.
    # ``senescence_start_fraction`` is the share of that cap after which
    # condition starts declining.
    max_age_ticks: int = 3120
    senescence_start_fraction: float = 0.70


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

    # Feeding state
    condition: float = 1.0        # Age/lifestyle multiplier (1.0 = healthy)
    efficiency: float = 0.6       # Effective digestion efficiency (0..1)
    digestion_capacity: float = 80.0  # Appetite: max food energy per contact
    energy_eaten_total: float = 0.0   # Lifetime food energy taken (pre-digestion)
    energy_absorbed_total: float = 0.0  # Lifetime food energy converted

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

    def refresh_efficiency(self, genotype: Genotype) -> None:
        """Recompute the effective digestion efficiency from gene × condition.

        ``condition`` drops as a bean ages (see :func:`apply_senescence`), so
        old beans convert less of each corpse into energy.
        """
        self.efficiency = max(
            0.0, min(1.0, genotype.digestion_efficiency * self.condition)
        )


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
    max_age_ticks=3120,
    senescence_start_fraction=0.70,
)


def create_default_phenotype(genotype: Genotype = DEFAULT_GENOTYPE) -> Phenotype:
    """Create a phenotype with default starting values."""
    phenotype = Phenotype(
        current_energy=genotype.energy_capacity,
        current_speed=0.0,
        velocity=(0.0, 0.0),
        age=0,
        is_dormant=False,
        condition=1.0,
        digestion_capacity=genotype.digestion_capacity,
    )
    phenotype.refresh_efficiency(genotype)
    return phenotype


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

    Lifespan is a two-stage draw: pick one of ``lifespan_tiers`` (so lifespans
    cluster at 70/75/.../100% of the species ceiling), then add a small
    ``lifespan_jitter`` and clamp to ``lifespan_fraction_floor`` and 1.0.
    """
    lifespan_fraction = rng.choice(ranges.lifespan_tiers)
    lifespan_fraction += rng.uniform(
        -ranges.lifespan_jitter, ranges.lifespan_jitter
    )
    lifespan_fraction = max(
        ranges.lifespan_fraction_floor, min(1.0, lifespan_fraction)
    )

    return Genotype(
        energy_capacity=rng.uniform(*ranges.energy_capacity),
        metabolic_rate=rng.uniform(*ranges.metabolic_rate),
        drag_coefficient=rng.uniform(*ranges.drag_coefficient),
        max_speed=rng.uniform(*ranges.max_speed),
        acceleration=rng.uniform(*ranges.acceleration),
        base_color=base_color,
        dormant_color=dormant_color,
        digestion_efficiency=rng.uniform(*ranges.digestion_efficiency),
        digestion_capacity=rng.uniform(*ranges.digestion_capacity),
        max_age_ticks=max(1, round(ranges.max_age_ticks * lifespan_fraction)),
        senescence_start_fraction=ranges.senescence_start_fraction,
    )


def apply_senescence(phenotype: Phenotype, genotype: Genotype) -> None:
    """Update ``condition`` from age and refresh digestion efficiency.

    Condition stays at 1.0 until ``senescence_start_fraction`` of the bean's
    own lifespan, then falls linearly to 0.0 at ``max_age_ticks``. A bean at
    its cap is removed by the caller; this only shapes the run-up.
    """
    max_age = genotype.max_age_ticks
    if max_age <= 0:
        condition = 1.0
    else:
        start = genotype.senescence_start_fraction * max_age
        if phenotype.age < start:
            condition = 1.0
        else:
            span = max(1e-9, max_age - start)
            condition = 1.0 - (phenotype.age - start) / span
    phenotype.condition = max(0.0, min(1.0, condition))
    phenotype.refresh_efficiency(genotype)


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