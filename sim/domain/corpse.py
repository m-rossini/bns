"""Corpses: dead beans turned into decaying, edible food.

A bean at zero energy is removed from the session and replaced by a
:class:`Corpse`. Corpses hold a flat amount of food energy (``basal_energy``),
lose ``decay_per_tick`` every tick, and can be eaten by living beans on
contact. Each feeding collision halves the corpse's remaining energy; the
bean converts the lost share at its phenotype ``efficiency``.

Once a corpse drops to ``rotten_fraction`` of its initial energy, the *next*
collision is rotten: the bean gains nothing and instead loses a fraction of the
energy it would have gained (clamped so it can never die), and the corpse is
removed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Sequence, Tuple

from sim.observability import get_logger, log_event

if TYPE_CHECKING:
    from sim.config import CorpseConfig
    from sim.domain.beans import Bean

logger = get_logger("corpse")


@dataclass(slots=True)
class Corpse:
    """A dead bean's remains, usable as food until it decays or is eaten."""

    id: int
    x: float
    y: float
    initial_energy: float
    energy: float
    source_bean_id: int
    gender: str = ""
    age: int = 0

    @property
    def energy_ratio(self) -> float:
        """Remaining share of the initial energy (0..1)."""
        if self.initial_energy <= 0.0:
            return 0.0
        return max(0.0, min(1.0, self.energy / self.initial_energy))

    def is_rotten(self, config: "CorpseConfig") -> bool:
        """True once the corpse is at or below the rotten threshold."""
        return self.energy <= self.initial_energy * config.rotten_fraction


def corpse_from_bean(
    bean: "Bean", corpse_id: int, config: "CorpseConfig"
) -> Corpse:
    """Create a corpse at the bean's position with the configured basal energy."""
    energy = float(config.basal_energy)
    return Corpse(
        id=corpse_id,
        x=bean.x,
        y=bean.y,
        initial_energy=energy,
        energy=energy,
        source_bean_id=bean.id,
        gender=bean.gender,
    )


def decay_corpses(
    corpses: Sequence[Corpse], config: "CorpseConfig"
) -> List[Corpse]:
    """Apply per-tick decay and drop corpses that reach zero energy."""
    survivors: List[Corpse] = []
    decayed = 0
    for corpse in corpses:
        corpse.age += 1
        corpse.energy -= config.decay_per_tick
        if corpse.energy <= 0.0:
            corpse.energy = 0.0
            decayed += 1
        else:
            survivors.append(corpse)
    if decayed:
        log_event(
            logger,
            "corpse.decayed",
            count=decayed,
            remaining=len(survivors),
        )
    return survivors


def _feed_collision(bean: "Bean", corpse: Corpse, config: "CorpseConfig") -> None:
    """Resolve one bean/corpse contact."""
    phenotype = bean.phenotype
    genotype = bean.genotype
    if phenotype is None or genotype is None:
        return

    if corpse.is_rotten(config):
        # Rotten: no energy is transferred; the bean pays a fraction of the
        # energy it would have gained, clamped so it can never be killed.
        would_be_lost = corpse.energy * config.collision_loss_fraction
        would_be_gain = would_be_lost * phenotype.efficiency
        penalty = would_be_gain * config.poison_gain_fraction
        floor = min(phenotype.current_energy, config.poison_energy_floor)
        phenotype.current_energy = max(floor, phenotype.current_energy - penalty)
        corpse.energy = 0.0
        log_event(
            logger,
            "corpse.rotted",
            level=logging.DEBUG,
            bean_id=bean.id,
            corpse_id=corpse.id,
            penalty=round(penalty, 3),
            energy=round(phenotype.current_energy, 3),
        )
        return

    lost = corpse.energy * config.collision_loss_fraction
    corpse.energy -= lost
    gained = lost * phenotype.efficiency

    from sim.domain.genotype import apply_energy_gain

    apply_energy_gain(phenotype, genotype, gained)
    log_event(
        logger,
        "corpse.consumed",
        level=logging.DEBUG,
        bean_id=bean.id,
        corpse_id=corpse.id,
        taken=round(lost, 3),
        gained=round(gained, 3),
        efficiency=round(phenotype.efficiency, 3),
        remaining=round(corpse.energy, 3),
    )


def feed_beans(
    beans: Sequence["Bean"],
    corpses: Sequence[Corpse],
    config: "CorpseConfig",
    radius: float,
) -> int:
    """Let overlapping living beans feed on corpses.

    Uses a spatial hash so the cost is roughly linear in the number of corpses
    and beans. Returns the number of contacts resolved this tick.
    """
    if not beans or not corpses:
        return 0

    reach = max(0.0, radius) * 2.0
    reach_sq = reach * reach
    cell = max(1.0, reach)

    buckets: Dict[Tuple[int, int], List[int]] = {}
    for index, corpse in enumerate(corpses):
        if corpse.energy <= 0.0:
            continue
        key = (int(corpse.x // cell), int(corpse.y // cell))
        buckets.setdefault(key, []).append(index)

    if not buckets:
        return 0

    contacts = 0
    for bean in beans:
        phenotype = bean.phenotype
        if phenotype is None or phenotype.current_energy <= 0.0:
            continue

        cx = int(bean.x // cell)
        cy = int(bean.y // cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nearby = buckets.get((cx + dx, cy + dy))
                if not nearby:
                    continue
                for index in nearby:
                    corpse = corpses[index]
                    if corpse.energy <= 0.0:
                        continue
                    ddx = bean.x - corpse.x
                    ddy = bean.y - corpse.y
                    if ddx * ddx + ddy * ddy > reach_sq:
                        continue
                    _feed_collision(bean, corpse, config)
                    contacts += 1
    return contacts
