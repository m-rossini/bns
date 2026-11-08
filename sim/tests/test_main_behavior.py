"""Behavior tests for the simulation loop in sim/main.py.

These cover the lifecycle after spawning: corpse decay plus feeding, the
extinction short-circuit, headless runs with and without an environment,
exit-time snapshots, and the headless entry point with save/load.
"""

from __future__ import annotations

import glob
import json
import os
from dataclasses import replace

from sim.components import GameState
from sim.config import (
    BeanPlacementConfig,
    EnvironmentConfig,
    PersistenceConfig,
    PoissonDiscConfig,
    SeasonConfig,
    SimulationConfig,
    WorldConfig,
)
from sim.container import Container
from sim.domain.corpse import Corpse
import sim.main as main_module
from sim.main import _advance_life, _save_on_exit, run_headless


def _make_config(**overrides):
    cfg = SimulationConfig(
        world=WorldConfig(width=200.0, height=200.0, cell_size=10.0),
        seasons=[
            SeasonConfig(
                name="Spring", ground_color=(96, 170, 88),
                base_temperature=14.0, temperature_swing=7.0,
                humidity=0.55, pressure_hpa=1012.0,
                sun_intensity=0.95, daylight_fraction=0.50,
                ground_meaning="growing season",
                weather_weights={"clear": 50, "cloudy": 50},
            ),
        ],
        bean_placement=BeanPlacementConfig(
            strategy_name="poisson_disc",
            density_tier="average",
            variance=0.0,
            seed=42,
            gender_ratios={"male": 50.0, "female": 50.0},
            gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
            bean_radius=5.0,
            poisson_disc=PoissonDiscConfig(),
        ),
        environment=EnvironmentConfig(
            weather_strategy="WeatherStrategy",
            season_strategy="SeasonStrategy",
            daynight_strategy="DayNightStrategy",
        ),
    )
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return cfg


def test_corpses_decay_while_neighbours_feed():
    """Leftovers rot each tick and nearby living beans take up energy."""
    container = Container(_make_config())
    session = container.session
    assert session.beans, "expected a spawned population to feed"
    diner = session.beans[0]
    diner.phenotype.current_energy = 100.0
    before = diner.phenotype.current_energy
    session.corpses.append(
        Corpse(id=1, x=diner.x, y=diner.y, initial_energy=200.0,
               energy=200.0, source_bean_id=999, gender="female")
    )

    extinct = _advance_life(session, container.config)

    assert extinct is False
    assert session.corpses[0].energy < 200.0  # decay happened
    assert diner.phenotype.current_energy > before  # feeding happened


def test_extinction_freezes_decay_and_feeding():
    """When the last bean dies, the run ends and leftovers stay untouched."""
    container = Container(_make_config())
    session = container.session
    session.state = GameState.PLAYING
    session.clock.paused = False  # otherwise the clock advances zero ticks
    for bean in session.beans:
        bean.phenotype.current_energy = 0.0  # everyone starves now
    session.corpses.append(
        Corpse(id=1, x=10.0, y=10.0, initial_energy=200.0,
               energy=200.0, source_bean_id=999, gender="female")
    )
    from sim.main import _step

    # No energy income this tick, so every zero-energy bean starves at once.
    # real_dt covers a full fixed step so the clock actually advances one tick.
    _step(session, container.environment, container.movement_strategy,
          None, 1.0 / 30.0, 1.0 / 30.0, container.config, max_ticks=1)

    assert session.state == GameState.END
    assert session.end_reason == "extinction"
    assert session.corpses[0].energy == 200.0  # skipped on extinction


def test_headless_run_works_without_an_environment(monkeypatch):
    """The loop only needs session + strategies; env output is optional."""
    monkeypatch.setenv("BEAN_HEADLESS_FRAMES", "2")
    container = Container(_make_config())
    session = container.session

    run_headless(
        session, None, container.movement_strategy,
        container.energy_strategy, 1.0 / 30.0, container.config,
        max_ticks=1,
    )

    assert session.state == GameState.PLAYING
    assert session.clock.tick > 0


def test_save_on_exit_disabled_writes_nothing(tmp_path):
    """Without save_on_exit the process exits without a final snapshot."""
    container = Container(_make_config())

    assert _save_on_exit(container, container.config) is None
    assert list(tmp_path.iterdir()) == []


def test_save_on_exit_writes_final_snapshot(tmp_path):
    """With save_on_exit a separate *-final.json snapshot is written."""
    container = Container(_make_config())
    config = replace(
        container.config,
        persistence=replace(
            container.config.persistence,
            directory=str(tmp_path),
            save_on_exit=True,
        ),
    )

    _save_on_exit(container, config)

    final = glob.glob(str(tmp_path / "*-final.json"))
    assert len(final) == 1
    with open(final[0], encoding="utf-8") as handle:
        assert json.load(handle)["schema_version"] == 1


def test_headless_run_stops_early_on_extinction(monkeypatch):
    """A world with no energy income goes extinct instead of running frames."""
    from sim.config import EnergyConfig
    from sim.implementations.energy.fixed_energy import FixedEnergyStrategy

    monkeypatch.setenv("BEAN_HEADLESS_FRAMES", "600")
    container = Container(_make_config())
    session = container.session
    for bean in session.beans:
        bean.phenotype.current_energy = 0.0
    no_income = FixedEnergyStrategy(
        config=EnergyConfig(strategy_name="fixed", energy_per_tick=0.0)
    )

    run_headless(
        session, container.environment, container.movement_strategy,
        no_income, 1.0 / 30.0, container.config, max_ticks=1,
    )

    assert session.state == GameState.END
    assert session.end_reason == "extinction"
    assert session.clock.tick < 600  # stopped early instead of running on


def test_save_on_exit_failure_does_not_crash_exit(tmp_path):
    """An unwritable snapshot directory is logged, not raised, on exit."""
    container = Container(_make_config())
    config = replace(
        container.config,
        persistence=replace(
            container.config.persistence,
            directory="/proc/bean-world-unwritable",
            save_on_exit=True,
        ),
    )

    assert _save_on_exit(container, config) is None
    assert list(tmp_path.iterdir()) == []


def test_main_with_corrupt_snapshot_exits_gracefully(monkeypatch, tmp_path):
    """A broken BEAN_LOAD file ends the run instead of raising."""
    import logging as std_logging

    bean_logger = std_logging.getLogger("bean")
    saved_propagate = bean_logger.propagate
    broken = tmp_path / "broken.json"
    broken.write_text("{not valid json", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BEAN_HEADLESS", "1")
    monkeypatch.setenv("BEAN_HEADLESS_FRAMES", "2")
    monkeypatch.setenv("BEAN_LOAD", str(broken))
    monkeypatch.delenv("BEAN_SAVE", raising=False)
    try:
        assert main_module.main() is None
        assert glob.glob(str(tmp_path / "saves" / "*.json")) == []
    finally:
        bean_logger.propagate = saved_propagate


def _log_text(tmp_path):
    """Combined text of the app log files written into the tmp cwd."""
    texts = []
    for path in glob.glob(str(tmp_path / "logs" / "*.log")):
        with open(path, encoding="utf-8") as handle:
            texts.append(handle.read())
    return "\n".join(texts)


def test_main_headless_saves_then_resumes(monkeypatch, tmp_path):
    """main() runs headless, autosaves, and a second run resumes that file."""
    import logging as std_logging

    bean_logger = std_logging.getLogger("bean")
    saved_propagate = bean_logger.propagate
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BEAN_HEADLESS", "1")
    monkeypatch.setenv("BEAN_HEADLESS_FRAMES", "2")
    monkeypatch.delenv("BEAN_LOAD", raising=False)
    monkeypatch.delenv("BEAN_SAVE", raising=False)
    try:
        main_module.main()
        saved = glob.glob(str(tmp_path / "saves" / "*.json"))
        assert len(saved) == 1
        assert "session.headless_finished" in _log_text(tmp_path)

        monkeypatch.setenv("BEAN_LOAD", saved[0])
        main_module.main()
        logs = _log_text(tmp_path)
        assert "persistence.loaded" in logs
        assert "session.headless_finished" in logs
    finally:
        bean_logger.propagate = saved_propagate
