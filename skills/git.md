# Git Skill

## Overview

This skill provides local git operations for the Bean World simulation project. It ensures that git repositories are properly managed with the main branch as the base, and that work is done via new branches or worktrees to never modify the main branch directly.
There is no GH Command, so you first try the MCP.

## Key Principles

1. **Main Branch Preservation**: The main branch is never modified directly. All work is done on new branches or worktrees.
2. **Branch Strategy**: If work is large, a worktree is suggested; otherwise, a branch is created.
3. **Cleanup**: After work is complete, local merge and worktree branches are cleaned up upon user request
4. **Full Lifecycle**: The skill handles the complete workflow: commit → push → PR → merge → clean → update main.

## Workflow

### 1. Repository Setup
- If no git repository exists, create one.
- Ensure the main branch is used as the base branch (not master).

### 2. Branch Management
- For small tasks: create a new branch.
- For large tasks: create a worktree.
- Let the user decide which approach to use.

### 3. Operations
- **Commit**: Stage and commit changes.
- **Push**: Push to remote.
- **PR**: Create a pull request.
- **Merge**: Merge the branch into main.
- **Cleanup**: Remove worktree and local changes.
- **Update Main**: After merge, update the main branch.
- **Full Finish**: Go from commit to Update Main

## Commands

- `git init` - Initialize a new git repository
- `git checkout -b <branch>` - Create and switch to a new branch
- `git worktree add <path> <branch>` - Create a worktree for a branch
- `git add <file>` - Stage changes
- `git commit -m "message"` - Commit changes
- `git push` - Push to remote
- `git pull` - Pull from remote
- `git merge <branch>` - Merge a branch into current
- `git branch <name>` - List branches
- `git status` - Check status

## Best Practices

- Always create a new branch for each feature or task.
- Never modify the main branch directly.
- Use worktrees for large-scale operations to avoid conflicts.
- Clean up worktrees and local changes after completion.
- Update main after successful merge.
