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
   ## Plan: RunContext + UXTracker Instrumentation (Intern-ready, TDD, Branching)

   This document is a step-by-step, highly detailed specification for implementing user-action tracking using a `RunContext` and `UXTracker`. Follow this as a development and testing checklist. Work must be done on a feature branch (never `main`) and follow TDD — create tests first, then implement. Use the exact file paths and commit messages described to keep history clean.

   ### Summary
   - Goal: Add full instrumentation for all user actions (dashboards) using a `UXTracker` that sends `Event` objects via the existing `EventSink` machinery.
   - Deliverables:
      - `src/observability/types.ts` (move `Event` and `EventType` here)
      - `src/observability/uxTracker.ts` (implementation with debouncing)
      - `src/runContext.ts` (holds `sessionId`, `uxTracker`, `worldWindow`, optional `game`)
      - Updated dashboard constructors to accept `RunContext`
      - Tests under `tests/observability/` and updated dashboard tests

   ### Branching & Process (Required)
   1. Check current branch:
       - `git status --porcelain` to ensure a clean working tree.
       - `git branch --show-current` to see the current branch.
   2. Create feature branch (if not on non-main already):
       - If on `main`, switch to a feature branch: `git checkout -b feat/ux-tracking-runcontext`
       - If on another branch, create a child branch: `git checkout -b feat/ux-tracking-runcontext`
   3. Make small, atomic commits with messages matching the steps below.

   ### Files To Create / Modify (High-level)
   - Add: `src/observability/types.ts`
   - Add: `src/observability/uxTracker.ts`
   - Add: `src/runContext.ts`
   - Update: `src/observability/eventSink.ts` and `src/observability/eventSinkFactory.ts` to import types from `observability/types.ts` instead of `src/config.ts`
   - Update: `src/dashboards/CommandsDashboard.ts` and `src/dashboards/DynamicConfigDashboard.ts` to accept `RunContext`
   - Update: `src/index.ts` to create the `RunContext`, initialize `UXTracker`, and wire into dashboards; assign `game` to context after instantiation.

   ### Detailed Implementation Steps

   1) Move observability types
       - Create `src/observability/types.ts` containing:
          - `export enum EventType { UX_ACTION = 'ux_action', SIMULATION_EVENT = 'simulation_event' }`
          - `export interface Event { id: string; timestamp: string; eventType: EventType; userId?: string; sessionId?: string; payload: Record<string, unknown>; }`
       - Update all observability modules to import from `./observability/types`.
       - Commit: `git add src/observability/types.ts && git commit -m "chore(observability): move Event and EventType to observability/types"`

   2) Implement `UXTracker` (TDD-first)
       - Create test: `tests/observability/uxTracker.test.ts`
          - The test should create a fake `EventSink` (a minimal class implementing `sendEvent` that stores events in an array) and assert that:
             - Calling `uxTracker.track('toggle_grid', { visible: true })` results in one `Event` reaching the sink.
             - The `Event` has `id` (UUID format), `timestamp` (ISO string), `eventType === EventType.UX_ACTION`, and `sessionId` === the `RunContext.sessionId` passed during initialization.
             - For high-frequency calls (simulate many `track` calls for `speed_change` within 200ms), only one event is emitted after the debounce period.
       - Implement `src/observability/uxTracker.ts` with the following signature:
          - `class UXTracker { constructor(sink: EventSink, sessionId: string, debounceMs = 300) {} track(action: string, payload: Record<string, unknown>): void }`
       - Behavior:
          - `track` should queue or debounce high-frequency events by `action` key. Implementation suggestion: maintain a map `pending: Map<string, {timeoutId:number, lastPayload: Record<string, unknown>}>`.
          - When debounce elapses for an `action`, call `sink.sendEvent({ id, timestamp, eventType: EventType.UX_ACTION, sessionId, payload: { action, ...lastPayload } })`.
          - For non-debounced events (button clicks, collapse toggles), call sink immediately.
       - Commit: `git add src/observability/uxTracker.ts tests/observability/uxTracker.test.ts && git commit -m "test(observability): add uxTracker tests; feat(observability): add UXTracker with debouncing"`

   3) Add `RunContext`
       - Create `src/runContext.ts` with the following class/interface:
          ```ts
          import Phaser from 'phaser';
          import { worldWindow } from './worldWindow';
          import { UXTracker } from './observability/uxTracker';

          export class RunContext {
             public sessionId: string;
             public uxTracker: UXTracker;
             public worldWindow = worldWindow;
             public game?: Phaser.Game;

             constructor(sessionId: string, uxTracker: UXTracker) {
                this.sessionId = sessionId;
                this.uxTracker = uxTracker;
             }
          }
          ```
       - Generate `sessionId` in `src/index.ts` when constructing the `RunContext` (per-load ID is required). Use a lightweight UUID generator; if none is available in the project, use a small helper:
          ```ts
          function uuidv4() {
             return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
                const r = Math.random() * 16 | 0;
                const v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
             });
          }
          ```
       - Commit: `git add src/runContext.ts && git commit -m "feat(observability): add RunContext container for UX tracking and sessionId"`

   4) Wire RunContext and UXTracker into `src/index.ts`
       - In `src/index.ts`, before creating Phaser game, create an `EventSink` for `EventType.UX_ACTION`:
          ```ts
          import { createEventSink } from './observability/eventSinkFactory';
          import { UXTracker } from './observability/uxTracker';
          import { RunContext } from './runContext';
          import { EventType } from './observability/types';

          const sessionId = uuidv4();
          const sink = createEventSink(EventType.UX_ACTION);
          const uxTracker = new UXTracker(sink, sessionId, 300);
          const runContext = new RunContext(sessionId, uxTracker);
          // Pass runContext into dashboards during scene.create()
          // After new Phaser.Game(config) assign game to runContext.game
          ```
       - Assign `runContext.game = game` after creating the Phaser instance (avoid circular init issues).
       - Commit: `git add src/index.ts && git commit -m "chore(bootstrap): initialize RunContext and UXTracker in index"`

   5) Update dashboard constructors and instrument events
       - `CommandsDashboard`:
          - Change constructor signature to:
             ```ts
             constructor(container: HTMLElement, initialGridState: boolean, onToggleGrid: (v:boolean)=>void, onTogglePause?: (p:boolean)=>void, runContext?: RunContext)
             ```
          - Store `this.runContext = runContext` and call `this.runContext?.uxTracker.track('toggle_grid', { visible: this.isGridVisible })` inside the toggle handler.
          - For pause/resume and collapse/expand, call `track` with action names: `pause_sim`, `resume_sim`, `commands_collapse`.
       - `DynamicConfigDashboard`:
          - Change constructor to accept `runContext?: RunContext` and store it.
          - Instrument the `input` handler for simulation speed to call `this.runContext?.uxTracker.track('speed_change', { speed: this.speed })`. Rely on `UXTracker` to debounce repeated `speed_change` events.
       - Commit: `git add src/dashboards && git commit -m "feat(dashboards): accept RunContext and instrument UX events"`

   6) Tests for dashboards
       - Update `tests/CommandsDashboard.test.ts` and `tests/DynamicConfigDashboard.test.ts`:
          - Instead of relying on DOM-only assertions, instantiate the dashboards with a fake `RunContext` whose `uxTracker` uses the fake `EventSink` from step 2.
          - Assert that user-action handlers (trigger button clicks, call collapse methods, simulate slider input) result in expected events being sent to the sink.
       - Commit tests and implementation fixes as needed: `git add tests && git commit -m "test(dashboards): assert UX events are emitted via RunContext"`

   7) Debounce specifics
       - Default debounce: `300ms` for high-frequency events (configurable via constructor argument in `UXTracker`).
       - Behavior: subsequent calls within debounce window update the pending payload; only the last payload is sent after the window.
       - Immediate sends: clicks and toggles should bypass debounce and be sent immediately.

   8) Local dev and test commands
       - Run tests frequently:
          ```bash
          npm run test
          ```
       - Lint / format as project uses (no global formatter specified here).

   9) Finalize and push
       - Run a final test run, fix any failing tests.
       - Push the branch:
          `git push origin feat/ux-tracking-runcontext`
       - Open a pull request with a description referencing the `RunContext`, `UXTracker`, and test coverage.

   ### Sample Event Schema (for implementers)
   ```json
   {
      "id": "uuid-v4",
      "timestamp": "2026-01-10T12:00:00.000Z",
      "eventType": "ux_action",
      "sessionId": "uuid-v4",
      "payload": { "action": "toggle_grid", "component": "CommandsDashboard", "visible": true }
   }
   ```

   ### Testing Notes and TDD Guidance (for the intern)
   - Write tests before code changes. Use a minimal `FakeEventSink` (implementation in tests) that records `sendEvent` calls.
   - Tests must be significant: assert shape and contents of events, and verify debouncing behavior.
   - Place tests in `tests/observability/` or update existing dashboard tests in `tests/` to use a fake `RunContext`.

   ### Code Review Checklist
   - Does the `uxTracker` generate `id` and `timestamp` for all events?
   - Are high-frequency events debounced correctly?
   - Are dashboard constructors updated with `RunContext` and no global state used?
   - Is `sessionId` generated per load and included in events?
   - Has `Phaser.Game` been assigned to `runContext.game` after creation?
   - Are tests passing and meaningful?

   ### Commit message conventions (use these exact prefixes)
   - `feat(...)`: new feature implementation
   - `test(...)`: tests added/changed
   - `chore(...)`: bootstrapping or misc chores
   - `fix(...)`: bug fixes after tests

   ### Example small change flow (intern-friendly)
   1. `git checkout -b feat/ux-tracking-runcontext`
   2. Add tests for `UXTracker` in `tests/observability/uxTracker.test.ts`.
   3. Implement `src/observability/uxTracker.ts` to satisfy tests.
   4. Commit: `git add -A && git commit -m "test(observability): add UXTracker tests; feat(observability): add UXTracker"`
   5. Continue with `RunContext` and dashboard wiring, iterating with tests.

   ---

   If you want, I can create the initial files and tests in this branch now and push them to a new feature branch — tell me to proceed and I will scaffold the files and run the test suite locally.
