# Modular Dashboard Specification & Grid Toggle Integration (Stepwise)

## 1. File Structure
- src/SimulationStatsDashboard.ts
- src/StatsDashboard.ts
- src/DynamicConfigDashboard.ts
- src/CommandsDashboard.ts
- src/index.ts (main entry, dashboard integration)
- index.html (dashboard containers)
- style.css (dashboard layout & collapsible styles)

**Do you want to continue and/or commit after this step?**

## 2. Class & Function Signatures

### SimulationStatsDashboard
```typescript
export class SimulationStatsDashboard {
  constructor(container: HTMLElement);
  render(): void;
  collapse(): void;
  expand(): void;
}
```

### StatsDashboard
```typescript
export class StatsDashboard {
  constructor(container: HTMLElement);
  render(): void;
  collapse(): void;
  expand(): void;
}
```

### DynamicConfigDashboard
```typescript
export class DynamicConfigDashboard {
  constructor(container: HTMLElement);
  render(): void;
  collapse(): void;
  expand(): void;
}
```

### CommandsDashboard (with grid toggle integration)
```typescript
export class CommandsDashboard {
  private gridToggleButton: HTMLButtonElement;
  private isGridVisible: boolean;

  constructor(container: HTMLElement, initialGridState: boolean, onToggleGrid: (visible: boolean) => void);

  render(): void;
  // Renders the toggle button and wires up its click event to call onToggleGrid
}
```

**Do you want to continue and/or commit after this step?**

## 3. Existing Grid Toggle Logic (to be moved)
- Currently in src/index.ts:
  - `setupGridToggle(getShowGrid, setShowGrid)` is called in the Phaser scene's create method.
  - `setupGridToggle` sets up the grid toggle button UI and event handler.
  - `setupGridButton` updates the button label and toggles grid visibility.

### Example of Current Logic:
```typescript
function setupGridToggle(getShowGrid: () => boolean, setShowGrid: (show: boolean) => void) {
  function initGridUI() {
    setContainerWidths();
    setupGridButton(getShowGrid, setShowGrid);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGridUI);
  } else {
    initGridUI();
  }
}

function setupGridButton(getShowGrid: () => boolean, setShowGrid: (show: boolean) => void) {
  const btn = document.getElementById('toggleGridBtn');
  if (btn) {
    btn.textContent = getShowGrid() ? 'Hide Grid' : 'Show Grid';
    btn.onclick = () => {
      const newShowGrid = !getShowGrid();
      btn.textContent = newShowGrid ? 'Hide Grid' : 'Show Grid';
      setShowGrid(newShowGrid);
    };
  }
}
```

**Do you want to continue and/or commit after this step?**

## 4. Refactor Plan
- Move the logic from `setupGridToggle` and `setupGridButton` into `CommandsDashboard.ts`.
- The `CommandsDashboard` will own the grid toggle button and its event handler.
- The button will use the same logic: update label, toggle state, and call the provided callback.

**Do you want to continue and/or commit after this step?**

## 5. index.ts Integration
- Instantiate each dashboard with its container.
- For CommandsDashboard, pass the current grid state and the grid toggle function.
- Call `render()` on each dashboard.

**Do you want to continue and/or commit after this step?**

---

This stepwise specification provides clear guidance for an intern to modularize the dashboards and refactor the grid toggle logic into the CommandsDashboard module, with checkpoints for your review and commits.
