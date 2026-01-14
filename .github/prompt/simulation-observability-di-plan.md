# Plan: Simulation Observability and Dependency Injection Refactor

This plan refactors the telemetry architecture to be polymorphic and decouples the simulation components from hardcoded configurations. By introducing a `SimulationContext` and utilizing constructor injection, we ensure the simulation is testable, extensible, and maintains strictly observed lifecycle telemetry.

## Step 1: Generic Tracker Infrastructure ✅
- **Definition**: Define a `Tracker` interface in `src/observability/types.ts`.
- **Implementation**: Create `src/observability/baseTracker.ts` to house shared logic like UUID generation, timestamping, and debouncing.
- **Refactor**: Update `src/observability/uxTracker.ts` to extend `BaseTracker`.
- **Verification**: Run `tests/observability/uxTracker.test.ts` to ensure compatibility.
- **Commit**: `feat(telemetry): implement polymorphic Tracker base and refactor UXTracker`

## Step 2: RunContext Tracker Registry ✅
- **Implementation**: Modify `src/runContext.ts` to replace `uxTracker` with a `trackers: Tracker[]` array.
- **Helper**: Add `getTracker<T>(type)` to `RunContext` for type-safe tracker retrieval.
- **Refactor**: Update any consumers of `runContext.uxTracker`.
- **Verification**: Run existing tests that use `RunContext`.
- **Commit**: `refactor(runContext): use generic tracker registry and helper`

## Step 3: Simulation Context & Tracker ✅
- **Tracker**: Create `src/observability/simulationTracker.ts` (extending `BaseTracker`).
- **Context**: Create `src/simulationContext.ts` to manage simulation dependencies including tracker and configs.
- **Integration**: Refactor `src/world.ts` to accept `SimulationContext` and log `world_created` on instantiation.
- **Integration**: Refactor `src/worldWindow.ts` to accept `SimulationContext` and log `simulation_start` on instantiation.
- **Dashboards**: Remove simulation object dependencies from dashboards. `StatsDashboard` now accepts stats data via render method.
- **Bootstrapping**: Update `src/index.ts` to initialize and inject `SimulationContext` into `worldWindow`.
- **Verification**: Add `tests/observability/simulationTracker.test.ts`.
- **Commit**: `feat(telemetry): add SimulationTracker and SimulationContext for dependency injection`

## Key Architectural Decisions

1. **No Global Singletons**: `WorldWindow` and `World` are no longer singletons. They are created with dependency injection.
2. **Polymorphic Trackers**: All trackers implement a common `Tracker` interface and extend `BaseTracker` for shared behavior.
3. **SimulationContext**: Acts as a service locator for simulation-wide concerns (tracking, config).
4. **Dashboard Decoupling**: Dashboards receive only the data they need via method parameters, not simulation objects.
5. **Sampling Strategy**: Simulation steps are sampled/debounced at 1-second intervals to avoid flooding the telemetry backend.

## Telemetry Events

- **`world_created`**: Fired when the World is instantiated. Includes dimensions.
- **`simulation_step`**: Fired periodically (sampled every 1s) with current tick and totalTime.
- **`simulation_start`**: Fired when the WorldWindow is initialized. Includes canvas dimensions.

## Testing Strategy

All tests follow TDD principles without mocks or spies:
- `SimulationTracker` is tested using a `MemorySink` that stores events.
- `World` and `WorldWindow` creation is verified by observing emitted events.
- Integration tests confirm the entire bootstrap pipeline works without hardcoded singletons.

## Test Results

- **Test Files**: 11 passed
- **Tests**: 30 passed
- **Coverage**: 85.23% statements, 87.41% lines

## Commit History

1. `feat(telemetry): implement polymorphic Tracker base and refactor UXTracker`
2. `refactor(runContext): use generic tracker registry and helper`
3. `feat(telemetry): add SimulationTracker and SimulationContext for dependency injection`
