# Bean World — Behaviour and Ground Rules

## Ground Rules

- Local skills take precedence over user/machine skills.
- **Git skill**: [`skills/git.md`](./skills/git.md) — the required local git
  workflow. Never commit to `main` directly; always work on a branch or in a
  worktree. Base branch is `main` (never `master`). Finish with
  commit → push → PR → merge → clean → update `main`.
- Keep documentation aligned with the code. If behaviour changes, update
  `README.md`, `diagrams.md` and `spec.md` in the same change set.
- Rendering never mutates domain state: `ArcadeView` reads a `GameSession`
  snapshot only.
- Never call `arcade.draw_text`; use cached `arcade.Text` objects.
- All tunables live in `sim/config.py`. Do not hardcode constants elsewhere.
- Verify with `make test` (local, headless) and `make verify` (in-container,
  headless) before opening a pull request.
- Never commit the `.venv`, caches, or ad-hoc screenshot scripts.

## Documentation

| File | Purpose |
|------|---------|
| [`README.md`](./README.md) | Current technical reference and usage |
| [`diagrams.md`](./diagrams.md) | Mermaid architecture diagrams |
| [`spec.md`](./spec.md) | Game specification aligned with the code |
| [`AGENTS.md`](./AGENTS.md) | Documentation index |
| [`TODO.md`](./TODO.md) | Task board |

## Project conventions

- Python 3.10+, `arcade` 3.3+. Domain and interfaces never import `arcade`.
- Coordinates are **world units**; cells are `WorldConfig.cell_size` units.
  The view applies its own world → screen scale.
- Readings are functions of position. Gradients come from
  `EnvironmentConfig` / `GradientConfig`, not from hardcoded directions.
- Business events are one line: `event=<name> key=value ...` under the
  `bean.*` logger namespace. The level comes from `BEAN_LOG_LEVEL`
  (Makefile: `LOG_LEVEL`, default `INFO`).
