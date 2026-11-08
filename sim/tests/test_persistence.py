"""Tests for versioned JSON snapshots and deterministic replay."""

from dataclasses import replace

from sim.components import GameState
from sim.config import (
    DEFAULT_CONFIG,
    BarrierConfig,
    CreationConfig,
    FixedAmountCreationConfig,
    GenotypeConfig,
    PersistenceConfig,
    SimulationConfig,
    WorldConfig,
)
from sim.container import Container
from sim.main import _step
from sim.persistence import (
    config_from_snapshot,
    load_snapshot,
    restore_snapshot,
    save_snapshot,
)


def _config() -> SimulationConfig:
    return replace(
        DEFAULT_CONFIG,
        world=WorldConfig(width=240.0, height=200.0, cell_size=10.0),
        barriers=BarrierConfig(
            density=0.02, min_span_cells=2, max_span_cells=4, seed=7
        ),
        creation=CreationConfig(
            strategy_name="fixed_amount",
            fixed_amount=FixedAmountCreationConfig(
                total_beans=24, placement_overshoot=3
            ),
            genotype_ranges=GenotypeConfig(),
            genotype_seed=7,
        ),
        persistence=PersistenceConfig(autosave_initial=False),
    )


def _advance(container, config: SimulationConfig, ticks: int) -> None:
    session = container.session
    session.state = GameState.PLAYING
    session.clock.paused = False
    step = 1.0 / config.tick_rate
    for _ in range(ticks):
        _step(
            session,
            container.environment,
            container.movement_strategy,
            container.energy_strategy,
            real_dt=step,
            fixed_step=step,
            config=config,
            max_ticks=1,
        )
        if session.state == GameState.END:
            break


def _bean_fingerprint(session):
    return [
        (
            bean.id,
            round(bean.x, 9),
            round(bean.y, 9),
            bean.gender,
            round(bean.phenotype.current_energy, 9),
            bean.phenotype.age,
            round(bean.genotype.max_age_ticks, 9),
        )
        for bean in session.beans
    ]


def test_config_round_trips_through_snapshot(tmp_path):
    config = _config()
    container = Container(config)
    path = save_snapshot(str(tmp_path / "snap.json"), container, config)

    payload = load_snapshot(path)
    decoded = config_from_snapshot(payload)

    assert decoded == config


def test_snapshot_restores_identical_state_and_replays_deterministically(tmp_path):
    config = _config()
    original = Container(config)
    path = save_snapshot(str(tmp_path / "snap.json"), original, config)
    payload = load_snapshot(path)

    restored = Container(config)
    restore_snapshot(payload, restored, config)

    assert len(restored.session.beans) == len(original.session.beans)
    assert restored.session.clock.tick == 0
    assert restored.session.initial_female == original.session.initial_female
    assert restored.session.initial_male == original.session.initial_male
    assert restored.session.beans == original.session.beans
    assert restored.world.barriers == original.world.barriers
    assert restored.environment.weather == original.environment.weather

    restore_snapshot(payload, original, config)

    _advance(original, config, 120)

    restore_snapshot(payload, restored, config)
    _advance(restored, config, 120)

    assert _bean_fingerprint(original.session) == _bean_fingerprint(
        restored.session
    )
    assert [
        (corpse.id, round(corpse.x, 9), round(corpse.y, 9))
        for corpse in original.session.corpses
    ] == [
        (corpse.id, round(corpse.x, 9), round(corpse.y, 9))
        for corpse in restored.session.corpses
    ]
    assert original.session.deaths_old_age == restored.session.deaths_old_age
    assert (
        original.session.deaths_starvation
        == restored.session.deaths_starvation
    )
