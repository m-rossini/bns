import { describe, it, expect, vi } from 'vitest';
import { SparseGrid } from '@/world/SparseGrid';
import { SimulationTracker } from '@/observability/simulationTracker';

describe('SparseGrid', () => {
  const mockTracker = {
    track: vi.fn()
  } as unknown as SimulationTracker;

  it('should initialize with given dimensions', () => {
    const grid = new SparseGrid({ width: 10, height: 10 }, mockTracker);
    expect(grid.width).toBe(10);
    expect(grid.height).toBe(10);
    expect(mockTracker.track).toHaveBeenCalledWith('grid_created', expect.any(Object));
  });

  it('should allow setting and getting a cell within bounds', () => {
    const grid = new SparseGrid({ width: 10, height: 10 }, mockTracker);
    grid.setCell(5, 5);
    const cell = grid.getCell(5, 5);
    expect(cell).toBeDefined();
    expect(cell?.x).toBe(5);
    expect(cell?.y).toBe(5);
  });

  it('should return undefined for non-existent cell', () => {
    const grid = new SparseGrid({ width: 10, height: 10 }, mockTracker);
    expect(grid.getCell(1, 1)).toBeUndefined();
  });

  it('should return all cells', () => {
    const grid = new SparseGrid({ width: 10, height: 10 }, mockTracker);
    grid.setCell(1, 1);
    grid.setCell(2, 2);
    const cells = grid.getAllCells();
    expect(cells.length).toBe(2);
    expect(cells).toContainEqual({ x: 1, y: 1 });
    expect(cells).toContainEqual({ x: 2, y: 2 });
  });

  it('should throw or handle out of bounds setCell', () => {
    const grid = new SparseGrid({ width: 10, height: 10 }, mockTracker);
    // Based on the plan, it says "Log error/throw if out of bounds"
    // I'll choose to throw for stricter TDD
    expect(() => grid.setCell(-1, 0)).toThrow();
    expect(() => grid.setCell(10, 0)).toThrow();
    expect(() => grid.setCell(0, -1)).toThrow();
    expect(() => grid.setCell(0, 10)).toThrow();
  });
});
