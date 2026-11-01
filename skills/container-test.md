# Container Test Skill

## Overview

This skill provides containerized test execution for any project. It runs automated tests inside a container to reproduce the exact runtime environment (Python, dependencies, OS) and catch environment-specific issues that may not appear on a developer workstation.

Container execution is the **preferred verification path** because it ensures consistent results across different development environments.

## When to Use

- Before opening a pull request: always run `make test-container`.
- When debugging environment-specific failures (missing packages, architecture differences, OpenGL/graphics issues, etc.).
- To verify that dependency files (requirements.txt, Containerfile, etc.) are correct.

## Prerequisites

- Podman (preferred) or Docker must be installed and the daemon/socket must be reachable.
- The `Containerfile` must build successfully.
- `requirements.txt` must list test dependencies (pytest, pytest-cov, coverage, etc.).

## Workflow

### 1. Build the Container Image

```bash
make build
```

### 2. Run the Full Test Suite with Coverage Inside the Container

```bash
make test-container
```

This:
1. Builds the container image (if not already built).
2. Mounts the project source into the container.
3. Installs test dependencies inside the container.
4. Runs `pytest sim/tests/ --cov=sim --cov-report=term-missing`.
5. Exits with the container's status (non-zero on test failure).

### 3. Alternative: Run Tests Locally (Development Only)

```bash
make test-pytest      # pytest only
make test-cov         # pytest with coverage report
make test             # compileall + pytest + coverage
```

## Coverage Thresholds

Aim for **high coverage** (e.g., 80%+) on domain and implementation code. New code should not reduce overall coverage. Focus on behavior-driven tests that exercise real code paths rather than coverage-only tests.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Container build fails | Check `Containerfile` apt/pip steps; ensure dependency files are valid. |
| `pytest` not found in container | Rebuild image after updating `Containerfile` pip install line. |
| Import errors in tests | Ensure source files are copied into the container image. |
| Headless OpenGL errors | Container runs headless by default; no X11 needed. |
| Coverage file write error | Ensure the container can write to the coverage output path. |

## Related

- [`skills/git.md`](./skills/git.md) - git workflow for committing test changes.
- [`Makefile`](./Makefile) - `test`, `test-pytest`, `test-cov`, `test-container` targets.
- [`Containerfile`](./Containerfile) - container image definition.