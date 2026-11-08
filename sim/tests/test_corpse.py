"""Tests for corpses: death, decay, feeding, and rotten collisions."""

import pytest

from sim.components import GameClock, GameSession, GameState
from sim.config import CorpseConfig, SimulationConfig
from sim.domain.beans import Bean
from sim.domain.corpse import (
    Corpse,
    corpse_from_bean,
    decay_corpses,
    feed_beans,
)
from sim.domain.genotype import (
    DEFAULT_GENOTYPE,
    create_default_phenotype,
)
from sim.main import _advance_life, _step


def _bean(bean_id=1, x=10.0, y=10.0, energy=100.0, efficiency=0.5, gender="female"):
    genotype = DEFAULT_GENOTYPE
    phenotype = create_default_phenotype(genotype)
    phenotype.current_energy = energy
    phenotype.efficiency = efficiency
    return Bean(
        id=bean_id,
        x=x,
        y=y,
        gender=gender,
        color=genotype.base_color,
        genotype=genotype,
        phenotype=phenotype,
    )


def _config(**kwargs):
    return CorpseConfig(**kwargs)


def test_corpse_from_bean_uses_flat_basal_energy():
    bean = _bean(energy=0.0, gender="male")
    corpse = corpse_from_bean(bean, corpse_id=7, config=_config(basal_energy=200.0))

    assert corpse.id == 7
    assert corpse.initial_energy == 200.0
    assert corpse.energy == 200.0
    assert corpse.source_bean_id == bean.id
    assert corpse.gender == "male"
    assert (corpse.x, corpse.y) == (bean.x, bean.y)


def test_decay_is_per_tick_and_removes_exhausted_corpses():
    corpse = Corpse(
        id=1, x=0.0, y=0.0, initial_energy=2.0, energy=2.0, source_bean_id=1
    )
    cfg = _config(decay_per_tick=1.0)

    survivors = decay_corpses([corpse], cfg)
    assert survivors == [corpse]
    assert corpse.energy == pytest.approx(1.0)
    assert corpse.age == 1

    survivors = decay_corpses(survivors, cfg)
    assert survivors == []
    assert corpse.energy == 0.0


def test_collision_halves_corpse_and_transfers_at_efficiency():
    bean = _bean(energy=100.0, efficiency=0.5)
    corpse = Corpse(
        id=1, x=bean.x, y=bean.y, initial_energy=200.0, energy=200.0, source_bean_id=9
    )

    contacts = feed_beans([bean], [corpse], _config(), radius=5.0)

    assert contacts == 1
    assert corpse.energy == pytest.approx(100.0)
    assert bean.phenotype.current_energy == pytest.approx(150.0)


def test_rotten_collision_penalizes_and_removes_corpse():
    bean = _bean(energy=100.0, efficiency=0.5)
    # 30 <= 20% of 200 -> rotten on contact.
    corpse = Corpse(
        id=1, x=bean.x, y=bean.y, initial_energy=200.0, energy=30.0, source_bean_id=9
    )

    contacts = feed_beans([bean], [corpse], _config(), radius=5.0)

    assert contacts == 1
    # Penalty = 0.5 * (30 * 0.5 * 0.5) = 3.75
    assert bean.phenotype.current_energy == pytest.approx(96.25)
    assert corpse.energy == 0.0


def test_rotten_poison_is_clamped_so_it_cannot_kill():
    bean = _bean(energy=0.5, efficiency=0.5)
    corpse = Corpse(
        id=1, x=bean.x, y=bean.y, initial_energy=200.0, energy=30.0, source_bean_id=9
    )

    feed_beans([bean], [corpse], _config(poison_energy_floor=1.0), radius=5.0)

    assert bean.phenotype.current_energy == pytest.approx(0.5)
    assert bean.phenotype.current_energy > 0.0


def test_dead_bean_becomes_corpse():
    cfg = SimulationConfig(corpse=_config(basal_energy=200.0))
    bean = _bean(energy=0.0)
    session = GameSession()
    session.beans = [bean]

    _advance_life(session, cfg)

    assert session.beans == []
    assert len(session.corpses) == 1
    assert session.corpses[0].initial_energy == 200.0
    assert session.next_corpse_id == 2


def test_advance_life_decays_and_removes_corpses():
    cfg = SimulationConfig(corpse=_config(basal_energy=1.0, decay_per_tick=1.0))
    session = GameSession()
    # Keep one living bean so the population is not extinct.
    session.beans = [_bean(x=1000.0, y=1000.0)]
    session.corpses = [
        Corpse(id=1, x=0.0, y=0.0, initial_energy=1.0, energy=1.0, source_bean_id=1)
    ]

    _advance_life(session, cfg)

    assert session.corpses == []


def test_extinction_freezes_everything_even_with_corpses():
    cfg = SimulationConfig(corpse=_config(basal_energy=200.0, decay_per_tick=5.0))
    session = GameSession(state=GameState.PLAYING)
    session.clock = GameClock(paused=False)
    session.beans = [_bean(energy=0.0)]
    corpse = Corpse(
        id=1, x=0.0, y=0.0, initial_energy=200.0, energy=200.0, source_bean_id=2
    )
    session.corpses = [corpse]

    ticks = _step(
        session, None, None, None,
        real_dt=1.0, fixed_step=1.0, config=cfg,
    )

    assert ticks == 1
    assert session.state == GameState.END
    assert session.end_reason == "extinction"
    assert session.clock.paused is True
    # No decay or feeding happens on the extinction tick.
    assert corpse.energy == 200.0

    frozen_tick = session.clock.tick
    assert _step(
        session, None, None, None,
        real_dt=1.0, fixed_step=1.0, config=cfg,
    ) == 0
    assert session.clock.tick == frozen_tick
    assert corpse.energy == 200.0
