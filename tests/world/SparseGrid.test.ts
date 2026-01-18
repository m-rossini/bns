import { describe, it, expect } from 'vitest';
import { SparseGrid } from '@/world/SparseGrid';

describe('SparseGrid', () => {
  it('should initialize with given dimensions', () => {
    const grid = new SparseGrid({ width: 10, height: 10 });
    expect(grid.width).toBe(10);
    expect(grid.height).toBe(10);
  });

  it('should allow setting and getting a cell within bounds', () => {
    const grid = new SparseGrid({ width: 10, height: 10 });
    grid.setCell(5, 5);
    const cell = grid.getCell(5, 5);
    expect(cell).toBeDefined();
    expect(cell?.x).toBe(5);
    expect(cell?.y).toBe(5);
  });

  it('should return undefined for non-existent cell', () => {
    const grid = new SparseGrid({ width: 10, height: 10 });
    expect(grid.getCell(1, 1)).toBeUndefined();
  });

  it('should return all cells', () => {
    const grid = new SparseGrid({ width: 10, height: 10 });
    grid.setCell(1, 1);
    grid.setCell(2, 2);
    const cells = grid.getAllCells();
    expect(cells.length).toBe(2);
    expect(cells).toContainEqual({ x: 1, y: 1 });
    expect(cells).toContainEqual({ x: 2, y: 2 });
  });

  it('should throw or handle out of bounds setCell', () => {
    const grid = new SparseGrid({ width: 10, height: 10 });
    // Based on the plan, it says "Log error/throw if out of bounds"
    // I'll choose to throw for stricter TDD
    expect(() => grid.setCell(-1, 0)).toThrow();
    expect(() => grid.setCell(10, 0)).toThrow();
    expect(() => grid.setCell(0, -1)).toThrow();
    expect(() => grid.setCell(0, 10)).toThrow();
  });
});
