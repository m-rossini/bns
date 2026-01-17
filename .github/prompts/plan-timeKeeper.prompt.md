## Detailed Plan: Robust Asynchronous Bootstrap & TimeKeeper System

This plan outlines the implementation of a "frictionless" timekeeper system and a refactor of the bootstrap sequence to ensure full telemetric visibility of the dynamic loading process.

### 1. Configuration Structure

Update [src/config.ts](src/config.ts) to include the dynamic provider configuration:

```typescript
export interface WorldConfig {
  readonly time: {
    readonly provider: string; // e.g., "SequentialTimeKeeper"
    readonly params: {
      readonly ticksPerYear: number;
      readonly initialTicks?: number;
    };
  };
}

export const worldConfig: Readonly<WorldConfig> = deepFreeze({
  time: {
    provider: 'SequentialTimeKeeper',
    params: {
      ticksPerYear: 360, // 360 ticks = 1 year
      initialTicks: 0
    }
  }
});
```

### 2. TimeKeeper Interface ([src/world/time/types.ts](src/world/time/types.ts))

The `ITimeKeeper` interface provides the logic for discrete simulation time.

- `tick(): void`: Increments the internal counter.
- `getTicks(): number`: Returns absolute simulation ticks.
- `getYearProgress(): number`: Returns a value between `0.0` and `1.0` representing normalized progress into the current year.
- `getTotalYears(): number`: Returns `ticks / ticksPerYear`.
- `getTicksPerYear(): number`: Utility to return the constant value.

### 3. Implementation: SequentialTimeKeeper ([src/world/time/SequentialTimeKeeper.ts](src/world/time/SequentialTimeKeeper.ts))

A standard linear time implementation.

- **Constructor**: `constructor(params: { ticksPerYear: number; initialTicks?: number })`
- **Logic**:
  - `yearProgress = (ticks % ticksPerYear) / ticksPerYear`
  - `totalYears = Math.floor(ticks / ticksPerYear)`

### 4. Phase 1: Critical Infrastructure (Synchronous)

- **Initialization**:
  - Initialize RUM/Logs immediately.
  - Create `EventSinks` (Console, OpenObserve).
  - Create `Trackers` (UX, Simulation).
  - Initialize `RunContext`.
- **Result**: `logger.info`, `logger.error`, and trackers are active before any business logic or dynamic loading occurs.

### 5. Phase 2: Dynamic Provider Resolution (Asynchronous)

Refactor [src/index.ts](src/index.ts) to handle the "frictionless" resolution:

```typescript
async function resolveTimeKeeper(config: WorldConfig['time']): Promise<ITimeKeeper> {
  const { provider, params } = config;
  try {
    logger.info(`Resolving TimeKeeper provider: ${provider}`);
    
    // Dynamic import mimics "classpath" scanning
    const module = await import(`./world/time/${provider}.ts`);
    const TimeKeeperClass = module[provider];
    
    if (!TimeKeeperClass) {
      throw new Error(`Class ${provider} not found in module`);
    }

    const instance = new TimeKeeperClass(params);
    logger.info(`TimeKeeper ${provider} successfully instantiated.`);
    return instance;
  } catch (error) {
    logger.error(`Failed to load TimeKeeper [${provider}]:`, { error });
    // Fallback or critical failure handling
    throw error;
  }
}
```

### 6. Phase 3: Simulation Assembly

- Pass the resolved `TimeKeeper` instance into the `SimulationContext`.
- Instantiate `World(simulationContext)`.
- Instantiate `WorldWindow(simulationContext)`.
- Initialize Phaser with the context ready.

### 7. TDD Strategy

1. **Unit Test**: Create `tests/world/time/SequentialTimeKeeper.test.ts`. 
2. **Behavior**: Verify that `tick()` updates `yearProgress` correctly (e.g., at 180/360 ticks, progress is 0.5).
3. **Integration**: Verify that `index.ts` can load a mock provider using the dynamic string pattern.
