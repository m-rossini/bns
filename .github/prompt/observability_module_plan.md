## Plan: Modularize Observability Code and Tests (Updated with Reference Updates)

### TL;DR
We will create a new module for observability-related code, move all relevant files and tests into appropriate directories, update all references to the moved files, and ensure functionality through testing. The process will follow a step-by-step approach, including branching, commits, and updates.

---

### Steps

#### 1. **Create a New Branch**
   - **Action**: Create a new branch to follow contribution guidelines.
   - **Command**: `git checkout -b feature/observability-module`
   - **Commit**: None (branch creation).

---

#### 2. **Create Observability Module**
   - **Action**: Create a new directory for observability code.
   - **Command**: `mkdir src/observability`
   - **Commit**: `git add src/observability && git commit -m "chore: create observability module directory"`

---

#### 3. **Move Observability Code**
   - **Action**: Move the following files into `src/observability/`:
     - [src/eventSink.ts](src/eventSink.ts)
     - [src/eventSinkFactory.ts](src/eventSinkFactory.ts)
     - [src/openObserveSink.ts](src/openObserveSink.ts)
     - [src/logger.ts](src/logger.ts)
   - **Command**: 
     ```bash
     mv src/eventSink.ts src/observability/
     mv src/eventSinkFactory.ts src/observability/
     mv src/openObserveSink.ts src/observability/
     mv src/logger.ts src/observability/
     ```
   - **Commit**: `git add src/observability && git commit -m "refactor: move observability code to module"`

---

#### 4. **Update References**
   - **Action**: Update all imports in the codebase to reflect the new file paths.
   - **Files to Update**:
     - [src/world.ts](src/world.ts)
     - [src/worldWindow.ts](src/worldWindow.ts)
     - [src/index.ts](src/index.ts)
     - [src/observability/openObserveSink.ts](src/observability/openObserveSink.ts)
     - [src/observability/eventSinkFactory.ts](src/observability/eventSinkFactory.ts)
   - **Steps**:
     - Replace imports like `import { EventSink } from '../eventSink';` with `import { EventSink } from './observability/eventSink';`.
     - Ensure all references to the moved files are updated.
   - **Commit**: `git add . && git commit -m "fix: update imports for observability module"`

---

#### 5. **Modularize Tests**
   - **Action**: Move all observability-related test files into `tests/observability/`:
     - [tests/eventSink.test.ts](tests/eventSink.test.ts)
     - [tests/eventSinkFactory.test.ts](tests/eventSinkFactory.test.ts)
     - [tests/openObserveSink.test.ts](tests/openObserveSink.test.ts)
   - **Command**:
     ```bash
     mkdir tests/observability
     mv tests/eventSink.test.ts tests/observability/
     mv tests/eventSinkFactory.test.ts tests/observability/
     mv tests/openObserveSink.test.ts tests/observability/
     ```
   - **Commit**: `git add tests/observability && git commit -m "test: modularize observability tests"`

---

#### 6. **Update Test References**
   - **Action**: Update all imports in the test files to reflect the new file paths.
   - **Steps**:
     - Replace imports like `import { EventSink } from '../../src/eventSink';` with `import { EventSink } from '../../src/observability/eventSink';`.
     - Ensure all references in the test files are updated.
   - **Commit**: `git add . && git commit -m "test: update imports for modularized tests"`

---

#### 7. **Run Tests**
   - **Action**: Run all tests to ensure no functionality is broken.
   - **Command**: `npm run test`
   - **Commit**: If fixes are needed, make changes and commit:
     - `git add . && git commit -m "fix: update tests for observability module"`

---

#### 8. **Final Review and Push**
   - **Action**: Review all changes and push the branch.
   - **Command**: `git push origin feature/observability-module`
   - **Commit**: None (push changes).

---

### Further Considerations
1. **Backward Compatibility**:
   - Ensure no breaking changes for external dependencies.
2. **Testing Guidelines**:
   - Follow TDD principles and ensure all tests are significant.
3. **Documentation**:
   - Update any relevant documentation to reflect the new module structure.