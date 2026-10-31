# Bean World Simulation 

[README.md](./README.md) - Technical details

[CLAUDE.md](./CLAUDE.md) - Behavior and ground rules

[spec.md](spec.md) - Initial technical project specification

## Ground Rules

- Local Skills take precedence over user/machine skills.
- **Git Skill**: `skills/git.md` - Local git operations for this project. Handles repository initialization, branch/worktree management, and full commit→push→PR→merge→clean→update workflow. Never modifies main directly; always creates new branches or worktrees. Use main as base branch (never master).
