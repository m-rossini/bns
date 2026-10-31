# Container Test Skill

## Overview

This skill runs Bean World tests inside the project container (podman/docker).
Container execution is the **preferred verification path** because it
reproduces the exact runtime environment (Python 3.10, Arcade, headless) and
catches issues that may not appear on a developer workstation.

## When to use

- Before opening a pull request: always run `make test-container`.
- When debugging environment-specific failures (OpenGL, missing packages,
  architecture differences).
- To verify that `requirements.txt` and `Containerfile` installs are correct.

## Prerequisites

- Podman (preferred) or Docker must be installed and the daemon/socket must be
  reachable.
- The `Containerfile` must build successfully (`make build`).
- `requirements.txt` lists pytest, pytest-cov, coverage.

## Workflow

### 1. Build the container image

```bash
make build
```

### 2. Run the full test suite with coverage inside the container

```bash
make test-container
```

This:
1. Builds the `bean-world:latest` image (if not already built).
2. Mounts the project source read-only into the container.
3. Runs `pytest sim/tests/ --cov=sim --cov-report=term-missing`.
4. Exits with the container's status (non-zero on test failure).

### 3. Alternative: run tests locally (development only)

```bash
make test-pytest      # pytest only
make test-cov         # pytest with coverage report
make test             # compileall + pytest + coverage
```

## Coverage thresholds

Aim for **100% line coverage** on `sim/domain/`, `sim/implementations/placement/`,
`sim/implementations/gender.py`, and `sim/domain/placement_utils.py`. New code
must not reduce overall coverage.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Container build fails | Check `Containerfile` apt/pip steps; ensure `requirements.txt` is valid. |
| `pytest` not found in container | Rebuild image after updating `Containerfile` pip install line. |
| Import errors in tests | Ensure `sim/` is copied into `/app/` in `Containerfile`. |
| Headless OpenGL errors | Container runs `BEAN_HEADLESS=1` by default; no X11 needed. |

## Related

- [`skills/git.md`](./skills/git.md) — git workflow for committing test changes.
- [`Makefile`](./Makefile) — `test`, `test-pytest`, `test-cov`, `test-container` targets.
- [`Containerfile`](./Containerfile) — container image definition.
