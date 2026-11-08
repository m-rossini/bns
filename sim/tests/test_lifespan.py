"""Tests for inherited lifespan, senescence and old-age death."""

import logging
import random
from dataclasses import replace

import pytest

from sim.components import GameClock, GameSession, GameState
from sim.config import GenotypeConfig, SimulationConfig
from sim.domain.beans import Bean
from sim.domain.genotype import (
    DEFAULT_GENOTYPE,
    create_default_phenotype,
    draw_genotype,
    apply_senescence,
)
from sim.main import _advance_life, _step


def _bean(genotype, energy=500.0, age=0):
    phenotype = create_default_phenotype(genotype)
    phenotype.current_energy = energy
    phenotype.age = age
    return Bean(
        id=1,
        x=10.0,
        y=10.0,
        gender="female",
        color=genotype.base_color,
        genotype=genotype,
        phenotype=phenotype,
    )


def test_lifespan_draw_is_capped_and_tiered():
    cfg = GenotypeConfig(
        max_age_ticks=1000,
        lifespan_fraction_floor=0.5,
        lifespan_tiers=(0.70, 0.80, 0.90, 1.00),
        lifespan_jitter=0.0,
    )
    rng = random.Random(0)

    ages = [
        draw_genotype(rng, cfg, (1, 2, 3)).max_age_ticks for _ in range(400)
    ]

    assert all(500 <= age <= 1000 for age in ages)
    fractions = {round(age / 1000, 2) for age in ages}
    assert {0.70, 0.80, 0.90, 1.00} <= fractions


def test_senescence_starts_at_configured_fraction():
    genotype = replace(
        DEFAULT_GENOTYPE,
        max_age_ticks=100,
        senescence_start_fraction=0.70,
        digestion_efficiency=0.60,
    )
    phenotype = create_default_phenotype(genotype)

    phenotype.age = 69
    apply_senescence(phenotype, genotype)
    assert phenotype.condition == pytest.approx(1.0)
    assert phenotype.efficiency == pytest.approx(0.60)

    phenotype.age = 85
    apply_senescence(phenotype, genotype)
    assert phenotype.condition == pytest.approx(0.5)
    assert phenotype.efficiency == pytest.approx(0.30)


def test_old_age_death_becomes_corpse_and_is_counted(caplog):
    genotype = replace(DEFAULT_GENOTYPE, max_age_ticks=10, senescence_start_fraction=0.5)
    bean = _bean(genotype, energy=500.0, age=9)
    session = GameSession()
    session.beans = [bean]

    with caplog.at_level(logging.INFO, logger="bean.main"):
        extinct = _advance_life(session, SimulationConfig())

    assert extinct is True
    assert session.beans == []
    assert len(session.corpses) == 1
    assert session.deaths_old_age == 1
    assert session.deaths_starvation == 0
    assert "cause=old_age" in caplog.text
    assert "age=10" in caplog.text


def test_living_bean_ages_exactly_once_per_tick_without_movement():
    genotype = replace(DEFAULT_GENOTYPE, max_age_ticks=1000)
    bean = _bean(genotype, energy=500.0, age=0)
    session = GameSession(state=GameState.PLAYING)
    session.clock = GameClock(paused=False)
    session.beans = [bean]

    _step(
        session, None, None, None,
        real_dt=1.0, fixed_step=1.0, config=SimulationConfig(),
    )

    assert bean.phenotype.age == 1
    assert session.beans == [bean]
