"""Versioned JSON snapshots for reproducible simulation runs.

A snapshot stores everything needed to recreate a game exactly: the full
configuration tree, the global RNG state, the session/clock, the world
barriers, every bean (genotype + phenotype), every corpse, every food morsel,
and the dynamic environment state. Snapshots are written after the initial
spawn (tick 0) and, optionally, when the game exits.

Runtime knobs:

* ``BEAN_SAVE`` — write the initial snapshot to this exact path.
* ``BEAN_LOAD`` — restore this snapshot instead of creating new beans.

When neither is set and ``PersistenceConfig.autosave_initial`` is true, one
file per game is written under ``PersistenceConfig.directory``.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, get_args, get_origin, get_type_hints

from sim import random as sim_random
from sim.components import Barrier, GameClock, GameSession, GameState
from sim.config import SimulationConfig
from sim.domain.beans import Bean
from sim.domain.corpse import Corpse
from sim.domain.food import Food
from sim.domain.genotype import Genotype, Phenotype
from sim.observability import get_logger, log_event

logger = get_logger("persistence")

_DISABLED_VALUES = {"0", "false", "no", "off", "none"}


# ----------------------------------------------------------------------
# Generic dataclass <-> JSON helpers
# ----------------------------------------------------------------------
def _encode_value(value: Any) -> Any:
    """Convert dataclasses/enums/tuples/dicts into JSON-friendly values."""
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _encode_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_encode_value(item) for item in value]
    if isinstance(value, list):
        return [_encode_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _encode_value(item) for key, item in value.items()}
    return value


def _decode_value(annotation: Any, value: Any) -> Any:
    """Reconstruct a value from JSON using the dataclass field annotation."""
    if value is None:
        return None
    if annotation is Any or annotation is None:
        return value

    origin = get_origin(annotation)
    if origin is Union:
        options = [arg for arg in get_args(annotation) if arg is not type(None)]
        if not options:
            return value
        return _decode_value(options[0], value)
    if origin in (list, List):
        (item_type,) = get_args(annotation) or (Any,)
        return [_decode_value(item_type, item) for item in value]
    if origin in (tuple, tuple):
        args = get_args(annotation)
        if not args:
            return tuple(value)
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_decode_value(args[0], item) for item in value)
        return tuple(_decode_value(arg, item) for arg, item in zip(args, value))
    if origin in (dict, Dict):
        key_type, value_type = get_args(annotation) or (Any, Any)
        return {
            _coerce_key(key_type, key): _decode_value(value_type, item)
            for key, item in value.items()
        }
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(value)
    if is_dataclass(annotation) and not isinstance(annotation, type):
        return _from_dict(annotation, value)
    if isinstance(annotation, type) and is_dataclass(annotation):
        return _from_dict(annotation, value)
    return value


def _coerce_key(annotation: Any, key: Any) -> Any:
    if annotation is int:
        return int(key)
    if annotation is float:
        return float(key)
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(key)
    return key


def _from_dict(cls, data: Dict[str, Any]):
    """Build a dataclass instance from a dict, decoding typed fields."""
    if not isinstance(data, dict):
        raise ValueError(f"Expected an object for {cls.__name__}, got {type(data).__name__}")
    hints = get_type_hints(cls)
    kwargs = {}
    for field in fields(cls):
        if field.name not in data:
            continue
        kwargs[field.name] = _decode_value(hints.get(field.name, Any), data[field.name])
    return cls(**kwargs)


# ----------------------------------------------------------------------
# Domain objects
# ----------------------------------------------------------------------
def _encode_phenotype(phenotype: Phenotype) -> Dict[str, Any]:
    return {
        "current_energy": phenotype.current_energy,
        "current_speed": phenotype.current_speed,
        "velocity": list(phenotype.velocity),
        "age": phenotype.age,
        "is_dormant": phenotype.is_dormant,
        "condition": phenotype.condition,
        "efficiency": phenotype.efficiency,
        "digestion_capacity": phenotype.digestion_capacity,
        "energy_eaten_total": phenotype.energy_eaten_total,
        "energy_absorbed_total": phenotype.energy_absorbed_total,
        "color": list(phenotype.color),
    }


def _decode_phenotype(data: Dict[str, Any]) -> Phenotype:
    phenotype = Phenotype(
        current_energy=float(data["current_energy"]),
        current_speed=float(data.get("current_speed", 0.0)),
        velocity=tuple(data.get("velocity", (0.0, 0.0))),
        age=int(data.get("age", 0)),
        is_dormant=bool(data.get("is_dormant", False)),
        condition=float(data.get("condition", 1.0)),
        efficiency=float(data.get("efficiency", 0.6)),
        digestion_capacity=float(data.get("digestion_capacity", 80.0)),
        energy_eaten_total=float(data.get("energy_eaten_total", 0.0)),
        energy_absorbed_total=float(data.get("energy_absorbed_total", 0.0)),
    )
    color = data.get("color")
    if color is not None:
        phenotype.color = tuple(color)
    return phenotype


def _encode_bean(bean: Bean) -> Dict[str, Any]:
    return {
        "id": bean.id,
        "x": bean.x,
        "y": bean.y,
        "gender": bean.gender,
        "color": list(bean.color),
        "vx": bean.vx,
        "vy": bean.vy,
        "genotype": _encode_value(bean.genotype) if bean.genotype is not None else None,
        "phenotype": _encode_phenotype(bean.phenotype) if bean.phenotype is not None else None,
    }


def _decode_bean(data: Dict[str, Any]) -> Bean:
    genotype = _from_dict(Genotype, data["genotype"]) if data.get("genotype") else None
    phenotype = _decode_phenotype(data["phenotype"]) if data.get("phenotype") else None
    return Bean(
        id=int(data["id"]),
        x=float(data["x"]),
        y=float(data["y"]),
        gender=data["gender"],
        color=tuple(data["color"]),
        vx=data.get("vx"),
        vy=data.get("vy"),
        genotype=genotype,
        phenotype=phenotype,
    )


# ----------------------------------------------------------------------
# Snapshot paths
# ----------------------------------------------------------------------
def _env_path(name: str) -> Optional[str]:
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or stripped.lower() in _DISABLED_VALUES:
        return None
    return stripped


def resolve_load_path(config: SimulationConfig) -> Optional[str]:
    """Path to load, honoring ``BEAN_LOAD`` before the config."""
    return _env_path("BEAN_LOAD") or config.persistence.load_path


def resolve_save_path(config: SimulationConfig) -> Optional[str]:
    """Path for the initial snapshot, or ``None`` when disabled."""
    if not config.persistence.enabled:
        return None
    explicit = _env_path("BEAN_SAVE") or config.persistence.save_path
    if explicit:
        return explicit
    if not config.persistence.autosave_initial:
        return None
    return default_save_path(config)


def default_save_path(config: SimulationConfig) -> str:
    """Timestamped per-game filename under the configured directory."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name = f"{config.persistence.filename_prefix}-{stamp}-{os.getpid()}.json"
    return str(Path(config.persistence.directory) / name)


def default_final_save_path(config: SimulationConfig) -> str:
    """Timestamped filename used by ``save_on_exit`` (never the initial file)."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name = (
        f"{config.persistence.filename_prefix}-{stamp}-{os.getpid()}-final.json"
    )
    return str(Path(config.persistence.directory) / name)


# ----------------------------------------------------------------------
# Save / load
# ----------------------------------------------------------------------
def save_snapshot(
    path: str,
    container,
    config: SimulationConfig,
) -> str:
    """Write a full snapshot atomically and return the path."""
    session = container.session
    payload = {
        "schema_version": config.persistence.schema_version,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "config": _encode_value(config),
        "rng_state": _encode_value(sim_random.get_rng().getstate()),
        "session": {
            "state": session.state.name,
            "end_reason": session.end_reason,
            "clock": _encode_value(session.clock),
            "start_time": session.start_time,
            "pause_time": session.pause_time,
            "exit_requested": session.exit_requested,
            "initial_female": session.initial_female,
            "initial_male": session.initial_male,
            "next_corpse_id": session.next_corpse_id,
            "deaths_old_age": session.deaths_old_age,
            "deaths_starvation": session.deaths_starvation,
        },
        "world": {
            "barriers": [_encode_value(barrier) for barrier in container.world.barriers],
        },
        "environment": container.environment.snapshot_state(),
        "beans": [_encode_bean(bean) for bean in session.beans],
        "corpses": [_encode_value(corpse) for corpse in session.corpses],
        "foods": [_encode_value(food) for food in session.foods],
    }

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, destination)

    log_event(
        logger,
        "persistence.saved",
        path=str(destination),
        tick=session.clock.tick,
        beans=len(session.beans),
        corpses=len(session.corpses),
        foods=len(session.foods),
    )
    return str(destination)


def load_snapshot(path: str) -> Dict[str, Any]:
    """Read and minimally validate a snapshot file."""
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Snapshot {path!r} is not a JSON object")
    if "config" not in payload or "session" not in payload:
        raise ValueError(f"Snapshot {path!r} is missing required sections")
    return payload


def config_from_snapshot(payload: Dict[str, Any]) -> SimulationConfig:
    """Rebuild the configuration tree stored in a snapshot."""
    return _from_dict(SimulationConfig, payload["config"])


def _decode_rng_state(data: List[Any]):
    version, internal, gauss = data
    return (int(version), tuple(int(part) for part in internal), gauss)


def restore_snapshot(
    payload: Dict[str, Any],
    container,
    config: SimulationConfig,
) -> None:
    """Apply a snapshot onto an already-built container."""
    session: GameSession = container.session

    session_data = payload["session"]
    session.state = GameState[session_data.get("state", "START")]
    session.end_reason = session_data.get("end_reason")
    session.clock = _from_dict(GameClock, session_data.get("clock", {}))
    session.start_time = float(session_data.get("start_time", 0.0))
    session.pause_time = float(session_data.get("pause_time", 0.0))
    session.exit_requested = bool(session_data.get("exit_requested", False))
    session.initial_female = int(session_data.get("initial_female", 0))
    session.initial_male = int(session_data.get("initial_male", 0))
    session.next_corpse_id = int(session_data.get("next_corpse_id", 1))
    session.deaths_old_age = int(session_data.get("deaths_old_age", 0))
    session.deaths_starvation = int(session_data.get("deaths_starvation", 0))

    session.beans = [_decode_bean(item) for item in payload.get("beans", [])]
    session.corpses = [
        _from_dict(Corpse, item) for item in payload.get("corpses", [])
    ]
    session.foods = [
        _from_dict(Food, item) for item in payload.get("foods", [])
    ]
    container.beans = session.beans

    barriers = [
        _from_dict(Barrier, item)
        for item in payload.get("world", {}).get("barriers", [])
    ]
    container.world.replace_barriers(barriers)

    container.environment.restore_state(payload.get("environment", {}))

    rng_state = payload.get("rng_state")
    if rng_state is not None:
        sim_random.get_rng().setstate(_decode_rng_state(rng_state))

    log_event(
        logger,
        "persistence.loaded",
        tick=session.clock.tick,
        beans=len(session.beans),
        corpses=len(session.corpses),
        foods=len(session.foods),
        state=session.state.name,
    )
