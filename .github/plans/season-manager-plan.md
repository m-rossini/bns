# Plan: Implement Season Manager with Configurable Strategies and Event Tracking

**Overview**: Build a season management system enabling environments to compute and distribute seasonal context to layers. Supports multiple strategies (hemispheric and global uniform seasons) with smooth transitions or discretized categories. Tracks all significant state changes (creation, season boundaries, strategy initialization) to OpenObserve. Uses LayerContext pattern to future-proof layers against configuration changes. Follows TDD with all tests preceding implementation.

---

## Phase 1: Type System & Interfaces

### New Types & Enums (in `src/world/simulationTypes.ts`)

#### `SeasonStrategy` enum
```
Values: HEMISPHERIC, GLOBAL_UNIFORM
Purpose: Selects which seasonal variation algorithm to apply
```

#### `TransitionMode` enum
```
Values: SMOOTH, DISCRETIZED
Purpose: Controls whether seasons transition smoothly or with discretized boundaries
```

#### `DiscreteSeasonName` enum
```
Values: SPRING, SUMMER, AUTUMN, WINTER
Purpose: Names for the four season categories
```

#### `SeasonalData` interface
**Properties**:
- `discreteSeason: DiscreteSeasonName` — Which of the four seasons we're currently in
- `continuousSeasonalFactor: number` — Smooth 0–1 value for interpolation (0 = spring peak, 0.25 = summer peak, 0.5 = autumn peak, 0.75 = winter peak)
- `yearProgress: number` — Current year progress 0–1 from TimeKeeper (normalized, independent of `ticksPerYear` configuration)
- `hemisphere: 'northern' | 'southern' | 'global'` — Which hemisphere or global if uniform strategy
- `transitionPhase: number` — Position within transition zone (0–1), useful for ease-in/out curves

#### `LayerContext` interface
**Properties**:
- `seasonalData: SeasonalData` — Current seasonal information
- `timeKeeper: TimeKeeper` — Reference to time keeper for layer to query ticks/year progress
- `gridWidth: number` — Width of simulation grid
- `gridHeight: number` — Height of simulation grid
- `simulationTracker: SimulationTracker` — For layers to emit their own events

**Purpose**: Encapsulates all environmental and contextual data needed by layers, protecting against future breaking changes.

#### `SeasonStrategy` interface (for strategy pattern)
**Methods**:
- `getSeasonForCell(x: number, y: number, yearProgress: number): SeasonalData` — Computes seasonal data for a specific cell at given year progress. Input: cell coordinates (x, y), year progress 0–1. Output: `SeasonalData` object. Called every tick for every cell query, no caching.
- `initialize(): void` — Called at SeasonManager creation after construction. Input: none. Output: none. Purpose: emit initialization events.

#### `HemisphericSeasonStrategy` class (implements `SeasonStrategy`)
**Properties**:
- `transitionMode: TransitionMode` — Whether transitions are smooth or discretized
- `tracker: SimulationTracker` — For event emission

**Methods** (all inherited from interface, but implements hemispheric logic):
- `getSeasonForCell(x: number, y: number, yearProgress: number): SeasonalData` — Uses y-coordinate as latitude proxy (y=0 = north pole, y=gridHeight/2 = equator, y=gridHeight = south pole). Applies seasonal offset: northern hemisphere peaks at yearProgress 0.5 (summer), southern hemisphere peaks at yearProgress 0.0/1.0 (summer opposite). Applies transition smoothing based on `transitionMode`.
- `initialize(): void` — Emits `season_strategy_initialized` event with strategy name.

#### `GlobalUniformSeasonStrategy` class (implements `SeasonStrategy`)
**Properties**:
- `transitionMode: TransitionMode` — Whether transitions are smooth or discretized
- `tracker: SimulationTracker` — For event emission

**Methods**:
- `getSeasonForCell(x: number, y: number, yearProgress: number): SeasonalData` — Ignores x, y coordinates, applies same seasonal curve globally. Single peak at yearProgress 0.5 (mid-year summer). Applies transition smoothing based on `transitionMode`.
- `initialize(): void` — Emits `season_strategy_initialized` event with strategy name.

---

## Phase 2: SeasonManager Class

### `SeasonManager` class (new file: `src/world/environments/SeasonManager.ts`)

**Temporal Note**: All yearProgress values (0.0–1.0) are normalized fractions of a year. The actual duration in ticks is determined by `ticksPerYear` from `src/config.ts`. This makes the season manager time-scale agnostic—strategies work correctly whether a year is 100 ticks, 360 ticks, or any other configured value.

**Properties**:
- `strategy: SeasonStrategy` — The currently active strategy (hemispheric or global)
- `tracker: SimulationTracker` — For event emission
- `lastDiscreteSeasonCache: Map<string, DiscreteSeasonName>` — Cache of last observed season per hemisphere/global (for detecting season boundary crossings). Key format: `"northern"`, `"southern"`, or `"global"`. Used to emit season-change events only when actual boundary crosses.
- `transitionMode: TransitionMode` — Smooth or discretized

**Constructor**:
- **Input**: `strategy: SeasonStrategy`, `tracker: SimulationTracker`, `transitionMode: TransitionMode`
- **Output**: new `SeasonManager` instance
- **Actions**: Store parameters, initialize `lastDiscreteSeasonCache`, call `strategy.initialize()`, emit `season_manager_created` event with strategy type and transition mode

**Methods**:

#### `getSeasonForCell(x: number, y: number, yearProgress: number): SeasonalData`
- **Input**: x (cell x-coordinate), y (cell y-coordinate), yearProgress (0–1 from TimeKeeper)
- **Output**: `SeasonalData` object
- **Actions**: Delegate to `strategy.getSeasonForCell()`, compute fresh every call (no caching of result itself). Detect if discrete season changed and emit `season_boundary_crossed` event if it did.

#### `createLayerContext(timeKeeper: TimeKeeper, gridWidth: number, gridHeight: number, yearProgress: number, x: number, y: number): LayerContext`
- **Input**: timeKeeper object, grid dimensions, current yearProgress, cell x/y coordinates
- **Output**: `LayerContext` object ready to pass to a layer
- **Actions**: Call `getSeasonForCell()`, wrap result with timekeeper and tracker refs, return populated `LayerContext`

#### `step(timeKeeper: TimeKeeper, gridWidth: number, gridHeight: number): void`
- **Input**: timeKeeper, grid dimensions
- **Output**: none
- **Actions**: Called by CompositeEnvironment each tick. Queries season for representative cells (e.g., equator) to trigger season-change event detection. This ensures boundary crossings are captured even if no layers query that specific region.

**Events Emitted**:
1. `season_manager_created` — At construction. Payload: `{ strategy: string, transitionMode: string }`
2. `season_boundary_crossed` — When discrete season changes for a hemisphere. Payload: `{ hemisphere: string, newSeason: string, yearProgress: number, tick: number }`
3. `season_strategy_initialized` — Emitted by strategy's `initialize()`. Payload: `{ strategy: string }`

---

## Phase 3: Update EnvironmentLayer Interface

### Modify `EnvironmentLayer` interface (in `src/world/simulationTypes.ts`)

**Current signature** (example, from AtmosphericTemperatureLayer):
```
constructor(...)
step(timeKeeper): void
getValueForCell(x, y): number
```

**New signature**:
```
constructor(context: LayerContext)
step(timeKeeper): void
getValueForCell(x: number, y: number): number
```

**Change**: Replace all environmental parameters with single `LayerContext` parameter in constructor.

**Rationale**: Future-proofs against additions (pressure zones, humidity fronts, etc.) without breaking layer contracts.

---

## Phase 4: Update CompositeEnvironment

### Modify `CompositeEnvironment` class (in `src/world/environments/CompositeEnvironment.ts`)

**New Properties**:
- `seasonManager: SeasonManager` — Created during initialization

**Constructor Changes**:
- **Input**: Same as before, plus extract `seasonStrategy` and `transitionMode` from config
- **Output**: new instance
- **Actions**: Create `SeasonManager` with chosen strategy, emit `composite_environment_created` event (existing or new)

**Modified `addLayer` method**:
- **Input**: `layer: EnvironmentLayer` (unchanged signature)
- **Output**: void
- **Actions**: 
  1. Remove old direct instantiation code (layers now instantiate themselves with LayerContext)
  2. Call `seasonManager.createLayerContext()` with current timekeeper state
  3. For implementation detail: layers must now be created externally with LayerContext, or we provide a factory method. **Recommendation**: Add `createLayerWithContext()` helper method to CompositeEnvironment that takes layer type and returns instantiated layer with context.

**Modified `step` method**:
- **Input**: timeKeeper (unchanged)
- **Output**: void
- **Actions**: Call `seasonManager.step()` before or after layer steps (recommend before, so season state is fresh for layer queries)

**New method `createLayerWithContext(layerType: string): EnvironmentLayer`**:
- **Input**: String identifier for layer type (`'temperature'`, `'humidity'`, `'luminosity'`)
- **Output**: Instantiated layer with populated LayerContext
- **Actions**: Query seasonManager for current context, instantiate appropriate layer class with context, return layer

**Events**:
- Existing events continue as-is
- New: coordinate with `SeasonManager` events (they propagate through tracker)

---

## Phase 5: Refactor Existing Layers

### Modify `AtmosphericTemperatureLayer` class (in `src/world/environments/layers/AtmosphericTemperatureLayer.ts`)

**Current Properties**:
- Internal seasonal computation (sinusoid-based)

**New Constructor Signature**:
- **Input**: `context: LayerContext`
- **Output**: new layer instance
- **Actions**: Store context, extract seasonal data for initialization, emit `layer_created` event with layer type

**Current `step` method**:
- **Changes**: Instead of computing seasonal factor from `timeKeeper.getYearProgress()`, call `context.seasonalData` which is already computed by SeasonManager. Store it as instance variable.

**Current `getValueForCell` method**:
- **Changes**: Use stored `context.seasonalData.continuousSeasonalFactor` instead of computing sinusoid independently. Layer can still apply its own transformations (latitudinal gradient, etc.) on top of this factor.

**Events**:
- `layer_created` — At construction. Payload: `{ layerType: 'temperature', contextProvided: true }`

### Modify `HumidityLayer` class (in `src/world/environments/layers/HumidityLayer.ts`)

**Same pattern as AtmosphericTemperatureLayer**:
- Accept `LayerContext` in constructor
- Use `context.seasonalData.continuousSeasonalFactor` instead of independent computation
- Emit `layer_created` event

**Events**:
- `layer_created` — At construction. Payload: `{ layerType: 'humidity', contextProvided: true }`

### Modify `LuminosityLayer` class (in `src/world/environments/layers/LuminosityLayer.ts`)

**Same pattern as previous layers**:
- Accept `LayerContext` in constructor
- Use `context.seasonalData.continuousSeasonalFactor`
- Emit `layer_created` event

**Events**:
- `layer_created` — At construction. Payload: `{ layerType: 'luminosity', contextProvided: true }`

---

## Phase 6: Configuration Updates

### Update `src/config.ts`

**New Configuration Properties**:
- `seasonStrategy: SeasonStrategy` — Enum value (`'HEMISPHERIC'` or `'GLOBAL_UNIFORM'`). **Type**: `SeasonStrategy`. **Default**: `'HEMISPHERIC'`. **Rationale**: Hemispheric variation is more realistic for multi-region simulation.
- `seasonTransitionMode: TransitionMode` — Enum value (`'SMOOTH'` or `'DISCRETIZED'`). **Type**: `TransitionMode`. **Default**: `'DISCRETIZED'`. **Rationale**: Discretized with smooth transition zones provides clear season names for debugging while maintaining smooth environmental curves.

**Note**: Per general.instructions.md, these are read-only at runtime—changes during development only.

---

## Phase 7: Testing Strategy (TDD Approach)

### Test File: `tests/world/SeasonManager.test.ts`

**Test Suite 1: SeasonManager Initialization**
- Test that `SeasonManager` is created with correct strategy type
- Test that `season_manager_created` event is emitted with correct metadata
- Test that strategy's `initialize()` is called during SeasonManager construction
- Test that `lastDiscreteSeasonCache` is populated with initial season values

**Test Suite 2: HemisphericSeasonStrategy - Basic Season Computation**
- Test season names at key year progress points: 0.0 (winter), 0.125 (spring), 0.25 (late spring), 0.375 (early summer), 0.5 (summer peak), 0.625 (fall), 0.75 (late fall), 0.875 (winter)
- Test northern hemisphere: summer peaks at yearProgress 0.5
- Test southern hemisphere: winter peaks at yearProgress 0.5 (opposite), summer at 0.0/1.0
- Test equator (y = gridHeight/2): seasons should blend (both hemispheres have equal weight)
- Test that `continuousSeasonalFactor` is smooth 0–1 curve

**Test Suite 3: HemisphericSeasonStrategy - Transition Modes**
- **DISCRETIZED mode**: Test that season categories change sharply at boundaries (spring → summer at 0.25, etc.)
- **DISCRETIZED with smooth transition zones**: Test that transition zones (±0.05 around boundaries) provide ease-in/out interpolation
- **SMOOTH mode**: Test that `continuousSeasonalFactor` is pure sinusoid with no step changes

**Test Suite 4: GlobalUniformSeasonStrategy - Basic Computation**
- Test that all cells return same season regardless of x, y coordinates
- Test season curve same as hemispheric northern hemisphere (peak at 0.5)
- Test that hemisphere in returned `SeasonalData` is always `'global'`

**Test Suite 5: Season Boundary Crossing Events**
- Test that `season_boundary_crossed` event fires when discrete season changes (e.g., spring to summer at yearProgress 0.25)
- Test event contains correct hemisphere, newSeason, yearProgress, and tick number
- Test that event fires only once per boundary crossing (not repeatedly)
- Test that boundaries are detected per hemisphere independently in hemispheric strategy

**Test Suite 6: LayerContext Creation**
- Test `createLayerContext()` returns object with all required properties
- Test that LayerContext includes current seasonalData, timeKeeper reference, grid dimensions, tracker
- Test that LayerContext is fresh each call (no stale data)

**Test Suite 7: SeasonManager.step() Method**
- Test that calling `step()` triggers boundary-crossing detection
- Test that representative cell queries (equator for hemispheric) are made
- Test that step() can be called repeatedly without error

**Test Suite 8: Latitude/Hemisphere Mapping**
- For hemispheric strategy, test that y-coordinate 0 is north pole, y=gridHeight/2 is equator, y=gridHeight is south pole
- Test seasonal offset: northern hemisphere should have 6-month lag from southern

### Test File: `tests/world/AtmosphericTemperatureLayer.test.ts` (update existing)

**Test Suite: Layer Initialization with LayerContext**
- Test that layer accepts `LayerContext` in constructor
- Test that `layer_created` event is emitted with `contextProvided: true`
- Test that layer stores and uses seasonal data from context

**Test Suite: Layer Value Computation with Seasonal Context**
- Test that `getValueForCell()` uses `context.seasonalData.continuousSeasonalFactor` (not independent sinusoid)
- Test that temperature peaks in summer (when `continuousSeasonalFactor` is high) and dips in winter (when low)
- Test that latitudinal gradient still applies on top of seasonal factor
- Test that all values remain within expected range (e.g., -20 to +50°C)

### Test File: `tests/world/HumidityLayer.test.ts` (update existing)

**Same pattern as temperature layer**:
- LayerContext initialization and event emission
- Uses seasonal data from context (inverse to temperature for realism)
- Values computed with seasonal factor + spatial variation

### Test File: `tests/world/LuminosityLayer.test.ts` (update existing)

**Same pattern as temperature layer**:
- LayerContext initialization
- Uses seasonal factor for luminosity variation
- Consistent values based on seasonal peak

### Test File: `tests/world/CompositeEnvironment.test.ts` (update existing)

**Test Suite: CompositeEnvironment with SeasonManager**
- Test that `seasonManager` is created during initialization
- Test `createLayerWithContext()` helper method returns layer with populated context
- Test that layers created via helper receive correct seasonal data
- Test that `step()` calls `seasonManager.step()`
- Test that season-related events propagate correctly

### Test File: `tests/world/LayerContext.test.ts` (new)

**Test Suite: LayerContext Interface**
- Test that LayerContext object contains all required properties (seasonalData, timeKeeper, grid dimensions, tracker)
- Test that LayerContext is immutable (properties cannot be reassigned after creation)
- Test that accessing context properties does not trigger errors

---

## Phase 8: Implementation Steps (for intern)

### Step 1: Set Up Branch and Create Type Definitions
1. Create new branch: `feature/season-manager`
2. Add new types to `src/world/simulationTypes.ts`:
   - `SeasonStrategy`, `TransitionMode`, `DiscreteSeasonName` enums
   - `SeasonalData`, `LayerContext` interfaces
   - `SeasonStrategy` interface (for strategy pattern)
3. **Commit**: "Add season manager types and interfaces"

### Step 2: Implement Strategy Classes
1. Create `src/world/environments/SeasonManager.ts` with:
   - `HemisphericSeasonStrategy` class
   - `GlobalUniformSeasonStrategy` class
2. Implement `getSeasonForCell()` methods following mathematical definitions (see Further Considerations for math)
3. Implement transition smoothing (ease-in/out for discretized mode, pure sinusoid for smooth)
4. **Run tests from Test Suite 2–4** (should fail initially; code to make pass)
5. **Commit**: "Implement season strategy classes"

### Step 3: Implement SeasonManager Core
1. Implement `SeasonManager` class in same file:
   - Constructor, properties
   - `getSeasonForCell()` with boundary-crossing detection
   - `createLayerContext()` helper
   - `step()` method
   - Event emission for all three event types
2. **Run tests from Test Suite 1, 5–7** (code to pass)
3. **Commit**: "Implement SeasonManager core and event tracking"

### Step 4: Update Layer Interface
1. Modify `EnvironmentLayer` interface in `simulationTypes.ts` to accept `LayerContext` in constructor
2. **Commit**: "Update EnvironmentLayer interface to accept LayerContext"

### Step 5: Update CompositeEnvironment
1. Add `seasonManager` property
2. Modify constructor to initialize seasonManager with strategy from config
3. Add `createLayerWithContext()` helper method
4. Modify `step()` to call seasonManager.step()
5. **Run tests from CompositeEnvironment test suite** (code to pass)
6. **Commit**: "Integrate SeasonManager into CompositeEnvironment"

### Step 6: Update Config
1. Add `seasonStrategy` and `seasonTransitionMode` properties to `src/config.ts`
2. Set sensible defaults
3. **Commit**: "Add season configuration parameters"

### Step 7: Refactor AtmosphericTemperatureLayer
1. Update constructor to accept `LayerContext` instead of individual parameters
2. Modify `step()` to use context's seasonal data
3. Modify `getValueForCell()` to use `context.seasonalData.continuousSeasonalFactor`
4. Add event emission for `layer_created`
5. **Run layer tests** (code to pass)
6. **Commit**: "Refactor AtmosphericTemperatureLayer to use LayerContext"

### Step 8: Refactor HumidityLayer
1. Same pattern as AtmosphericTemperatureLayer
2. **Run layer tests** (code to pass)
3. **Commit**: "Refactor HumidityLayer to use LayerContext"

### Step 9: Refactor LuminosityLayer
1. Same pattern as AtmosphericTemperatureLayer
2. **Run layer tests** (code to pass)
3. **Commit**: "Refactor LuminosityLayer to use LayerContext"

### Step 10: Verify All Tests Pass
1. Run full test suite: `npm test`
2. Verify coverage is adequate (aim for >80%)
3. Verify all events are emitted correctly by checking tracker calls in tests
4. **Commit**: "Verify all tests pass and coverage meets standards" (if any fixes needed)

### Step 11: Integration Testing (Optional but Recommended)
1. Create simple integration test scenario: world with hemispheric seasons, run multiple ticks, verify layer values change seasonally
2. Verify events are emitted to OpenObserve format correctly
3. **Commit**: "Add integration tests for season system" (if tests added)

---

## Further Considerations

### 1. Hemispheric Season Mathematical Definition

**Important**: All temporal references below (season windows, transition zones, offsets) are expressed as fractions of the year (0.0–1.0), where `yearProgress` is provided by `TimeKeeper`. The actual duration of these periods in ticks is determined by the `ticksPerYear` configuration parameter from `src/config.ts`. For example, if `ticksPerYear: 360`, then 0.25 of the year represents 90 ticks; if `ticksPerYear: 100`, it represents 25 ticks.

For `HemisphericSeasonStrategy` with transition mode `DISCRETIZED` + smooth transitions:

**Season windows** (yearProgress ranges, illustrative):
- **Spring**: 0.0–0.25 (peak effect at 0.125)
- **Summer**: 0.25–0.5 (peak effect at 0.375)
- **Autumn**: 0.5–0.75 (peak effect at 0.625)
- **Winter**: 0.75–1.0 (peak effect at 0.875)

**Northern Hemisphere Seasonal Factor**:
- Base curve: `sin(yearProgress * 2π)` (peaks at yearProgress 0.5)
- Transition zone width: ±0.05 around each boundary (adjustable, represents 5% of year)
- Within transition zone: apply ease-in/out (e.g., smoothstep function) for interpolation

**Southern Hemisphere Seasonal Factor** (opposite offset by half year):
- Base curve: `sin((yearProgress + 0.5) * 2π)` (peaks at yearProgress 0.0/1.0, offset by 0.5 of the year)
- Offset represents temporal opposite of northern hemisphere

**Equator blending**:
- Detect latitude position from y-coordinate
- Blend northern and southern factors (50-50 at equator, 0-100 at poles)

**Smooth mode** (no discretization):
- Just apply base sinusoid curves without transition zones or discrete season names

### 2. Event Tracking Completeness

Ensure these events are emitted:
1. **season_manager_created** — On SeasonManager construction
2. **season_strategy_initialized** — When strategy initializes
3. **season_boundary_crossed** — Only when discrete season name changes per hemisphere
4. **layer_created** — When each layer is instantiated (existing, now with context info)
5. **composite_environment_created** — Existing, confirm seasonManager is created beforehand

### 3. Performance Note

`getSeasonForCell()` is called every tick for every cell query (no caching). This is acceptable because:
- Computation is simple math (sinusoid + blending)
- Grid sizes are typically small (hundreds to thousands of cells)
- Caching would add complexity with stale-data risks

Monitor performance during integration testing; if needed, add optional caching layer later.

### 4. Future Extensions

LayerContext design allows for:
- Adding new environmental attributes (pressure systems, humidity fronts, etc.)
- Extending strategies (more than 2 season types)
- Per-cell configuration overrides
- Seasonal event categories (migration triggers, breeding seasons, etc.)

All without breaking layer contracts.
