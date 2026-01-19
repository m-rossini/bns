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
- Code MUST follow the existing style and conventions of the project.
- In between phases a commit needs to be done with a clear and concise message describing the changes made.

## Coding Standards
- All code MUST be written in TypeScript.
- Public methods cannot have boolean parameters.
- Imports must NEVER be local and must be at the beginning of the file


## Testing Guidelines
- All new features and bug fixes MUST include appropriate tests.
- Tests MUST be written using the testing framework specified in the project
- All tests MUST pass before submitting a pull request.
- Tests MUST be significant, and MUST NOT access internal state via spies or mocks or dubs.
- All test files MUST be placed in the `tests/` directory, not mixed with production code.

## Planning Guidelines
 - When in plan mode, let's consider pros and cons of each feature or change.
 - Let's always think about the future implications of our design choices.
 - Always consider logging and monitoring and tracing and metrics from the start
 - When asked to build a final plan, make a very detailed plan to be implemented by an unexperienced intern
 - Deatiled plan implies:
    - Step by step instructions
    - All interfaces and classes and types described
    - All methods described with input and output
    - Properties described with types
    - No implementation code, just design and plan, but example code is allowed for illustration on top of the interfaces and types
    