---
applyTo: '**'
---

# General Contribution Instructions

## Designing Guidelines
- All new features and any changes MUST be discussed before implementation.
- Configuration MUST NOT BE CHANGED during runtime, they are ALWAYS read only in runtime, but we can change to add or modify parameters during development.

## Pre Work Guidelines
- Development MUST be done in other branch than `main`, implying NEVER , EVER make changes in main

## Development Guidelines
- Development MUST be done in TDD style.

## Testing Guidelines
- All new features and bug fixes MUST include appropriate tests.
- Tests MUST be written using the testing framework specified in the project
- All tests MUST pass before submitting a pull request.
- Tests MUST be significant, and MUST NOT access internal state via spies or mocks or dubs.
- All test files MUST be placed in the `tests/` directory, not mixed with production code.