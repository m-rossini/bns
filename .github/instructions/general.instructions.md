---
applyTo: '**'
---

# General Contribution Instructions

## Designing Guidelines
- All new features and any changes MUST be discussed before implementation.
- Configuration MUST NOT BE CHANGED, they are ALWAYS read only.

## Pre Work Guidelines
- Development MUST be done in other branch than `main`.

## Development Guidelines
- Development MUST be done in TDD style.

## Testing Guidelines
- All new features and bug fixes MUST include appropriate tests.
- Tests MUST be written using the testing framework specified in the project
- All tests MUST pass before submitting a pull request.
- Tests MUST be significant, and MUST NOT access internal state via spies or mocks or dubs.