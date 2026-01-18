# Plan: Sparse Grid Architecture and Render Relocation

## Objective
Decouple the business logic of the simulation (grid/cells) from its visual representation (Phaser/Pixels). The simulation should operate on logical cell coordinates within defined boundaries, while the presentation layer handles the mapping to screen pixels.

---

## 1. Type Definitions

### 1.1 `src/world/simulationTypes.ts`
Add the following interfaces to represent the logical state of the world:

```typescript
export interface Cell {
  readonly x: number;
  readonly y: number;
}

/**
 * Bounds for the logical simulation space.
 */
export interface WorldBounds {
  readonly width: number;  // Maximum number of cells in X
  readonly height: number; // Maximum number of cells in Y
}
```

### 1.2 `src/config.ts`
Update `WorldConfig` to include the logical dimensions of the world.

```typescript
export interface WorldConfig {
  readonly dimensions: {
    readonly width: number;  // cells
    readonly height: number; // cells
  };
  // ... existing time config
}
```

---

## 2. Simulation Layer: `SparseGrid` implementation

### 2.1 File: `src/world/SparseGrid.ts`
This class manages the collection of cells and enforces boundaries.

**Fields:**
- `private readonly cells: Map<string, Cell>`: Internal map where key is `"x,y"`.
- `public readonly width: number`: Boundary from config.
- `public readonly height: number`: Boundary from config.

**Methods:**
- `constructor(width: number, height: number)`: Initialize with boundaries.
- `setCell(x: number, y: number): void`:
    - **Validation**: Check if `0 <= x < width` and `0 <= y < height`. Log error/throw if out of bounds.
    - **Storage**: Add/Overwrite `Cell` in the map.
- `getCell(x: number, y: number): Cell | undefined`: Retrieve cell.
- `getAllCells(): Cell[]`: Return an array of all active cells for the renderer.
- `private generateKey(x: number, y: number): string`: Helper for map keys.

---

## 3. Simulation Layer: Update `World`

### 3.1 File: `src/world/world.ts`
**Fields:**
- `public readonly grid: SparseGrid`: The simulation's grid.

**Logic:**
- In the `constructor`, initialize `this.grid = new SparseGrid(context.worldConfig.dimensions.width, context.worldConfig.dimensions.height)`.

---

## 4. Presentation Layer: Refactor `WorldWindow`

### 4.1 File: `src/worldWindow.ts`
Move all pixel-drawing logic from `src/grid.ts` into this class.

**Methods:**
- `draw(graphics: Phaser.GameObjects.Graphics): void`:
    - `graphics.clear()`
    - If `!this.state.showGrid`, return.
    - Call `drawLines(graphics)` or `drawCells(graphics)` based on `config.gridDrawMode`.
- `private drawLines(graphics: Phaser.GameObjects.Graphics): void`:
    - Draw the mesh lines using `this.config.cellSize` as the spacing.
    - Loop up to `canvasWidth` and `canvasHeight`.
- `private drawCells(graphics: Phaser.GameObjects.Graphics): void`:
    - Retrieve all cells from `this.world.grid.getAllCells()`.
    - Loop through cells:
        - Map `logicalX` to `screenX = cell.x * this.config.cellSize`.
        - Map `logicalY` to `screenY = cell.y * this.config.cellSize`.
        - Draw a rectangle using `graphics.fillRect(screenX, screenY, cellSize, cellSize)`.
- `private hexToColor(hex: string): number`: Private helper migrated from `grid.ts`.

---

## 5. Integration and Cleanup

### 5.1 Update `src/index.ts`
- Remove import and usage of `drawGrid`.
- In the Phaser `create()` function, set up `gridGraphics`.
- In the `update()` loop or within `CommandsDashboard` callbacks, call `worldWindow.draw(gridGraphics)`.

### 5.2 File Deletion
- Delete `src/grid.ts` entirely.

---

## 6. Testing (TDD)

### 6.1 `tests/world/SparseGrid.test.ts`
- Verify that `setCell` stores cells correctly.
- Verify that `setCell` rejects coordinates outside the `width/height` boundaries.
- Verify that `getAllCells` returns the correct count.

### 6.2 Update Rendering Tests
- Update `tests/grid.test.ts` (can be renamed to `tests/worldWindow.test.ts`) to test `worldWindow.draw`.
- Mock the `SparseGrid` to return specific cells and verify the `graphics` object received the correct `fillRect` calls.
