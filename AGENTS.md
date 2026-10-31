# Bean World — Documentation Index

Start here, then follow the link for the level of detail you need.

| File | Purpose |
|------|---------|
| [`README.md`](./README.md) | Current technical reference: architecture, configuration, logging, rendering, verification. **Start here.** |
| [`diagrams.md`](./diagrams.md) | Mermaid class, sequence, flow and state diagrams of the current code. |
| [`specs/spec.md`](./specs/spec.md) | Game specification, kept aligned with the implementation. |
| [`specs/bean_placement_strategy_spec.md`](./specs/bean_placement_strategy_spec.md) | Bean initial placement & gender system specification. |
| [`CLAUDE.md`](./CLAUDE.md) | Behaviour and ground rules for agents. |
| [`TODO.md`](./TODO.md) | Task board for the current change set. |
| [`skills/git.md`](./skills/git.md) | Local git workflow: branch/worktree → commit → push → PR → merge → clean. |

## Reading order

1. `README.md` — what the project is and how to run it.
2. `diagrams.md` — how the pieces talk to each other.
3. `specs/spec.md` — defaults, interfaces and detailed behaviour.

## Ground rules

See [`CLAUDE.md`](./CLAUDE.md). In short: never commit to `main` directly, use
the git workflow in `skills/git.md`, and keep documentation aligned with the
code.
