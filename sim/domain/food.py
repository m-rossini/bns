"""Food morsels beans can eat.

Food is the renewable energy source: morsels spawn with random energy values,
beans nibble them on contact, and a spawn strategy keeps the total food energy
around a configured target. Corpses are the other food source (see
:mod:`sim.domain.corpse`); food differs by being renewable, seasonal and
digestion-capped per contact.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


@dataclass(slots=True)
class Food:
    """One edible morsel."""

    id: int
    x: float
    y: float
    radius: float
    energy: float
    initial_energy: float

    @property
    def energy_ratio(self) -> float:
        """Remaining share of the initial energy (0..1)."""
        if self.initial_energy <= 0.0:
            return 0.0
        return max(0.0, min(1.0, self.energy / self.initial_energy))


def total_energy(foods: Sequence[Food]) -> float:
    """Current food energy in the world, in energy units."""
    return sum(food.energy for food in foods)


def seasonal_abundance(sun_intensity: float, daylight_fraction: float) -> float:
    """Seasonal food-abundance multiplier from the season's sun profile.

    Uses the already-varied seasonal baselines (year-to-year variation flows
    through automatically): bright long days grow more food, dim short days
    grow less. Spring sits near 0.85, summer above 1.1, autumn near 0.7 and
    winter near 0.4.
    """
    return max(
        0.15, min(1.6, sun_intensity * (0.4 + daylight_fraction))
    )


def feed_beans_on_food(
    beans: Sequence["Bean"],
    foods: Sequence[Food],
    bean_radius: float,
) -> int:
    """Let overlapping living beans nibble food.

    Each contact is capped by the bean's own ``digestion_capacity`` (appetite)
    and by the room left in its energy store; the remainder stays on the
    morsel for later visits. Absorbed energy is scaled by the phenotype's
    ``efficiency`` and both the eaten and the absorbed totals are tracked on
    the phenotype for future evolution. Uses a spatial hash so the cost is
    roughly linear in the number of foods and beans. Returns the number of
    contacts resolved this tick.
    """
    if not beans or not foods:
        return 0

    reach = max(0.0, bean_radius) * 2.0
    reach_sq = reach * reach
    cell = max(1.0, reach)

    buckets: Dict[Tuple[int, int], List[int]] = {}
    for index, food in enumerate(foods):
        if food.energy <= 0.0:
            continue
        key = (int(food.x // cell), int(food.y // cell))
        buckets.setdefault(key, []).append(index)

    if not buckets:
        return 0

    contacts = 0
    for bean in beans:
        phenotype = bean.phenotype
        genotype = bean.genotype
        if phenotype is None or genotype is None:
            continue
        if phenotype.current_energy <= 0.0:
            continue

        cx = int(bean.x // cell)
        cy = int(bean.y // cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nearby = buckets.get((cx + dx, cy + dy))
                if not nearby:
                    continue
                for index in nearby:
                    food = foods[index]
                    if food.energy <= 0.0:
                        continue
                    ddx = bean.x - food.x
                    ddy = bean.y - food.y
                    if ddx * ddx + ddy * ddy > reach_sq:
                        continue
                    room = genotype.energy_capacity - phenotype.current_energy
                    if room <= 0.0:
                        break
                    intake = min(
                        food.energy, phenotype.digestion_capacity, room
                    )
                    if intake <= 0.0:
                        continue
                    absorbed = intake * phenotype.efficiency
                    phenotype.current_energy = min(
                        genotype.energy_capacity,
                        phenotype.current_energy + absorbed,
                    )
                    phenotype.energy_eaten_total += intake
                    phenotype.energy_absorbed_total += absorbed
                    food.energy -= intake
                    contacts += 1
    return contacts
