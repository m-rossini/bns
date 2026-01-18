import { Cell, WorldBounds, IGrid } from '@/world/simulationTypes';
import { SimulationTracker } from '@/observability/simulationTracker';

export class SparseGrid implements IGrid {
  private readonly cells: Map<string, Cell> = new Map();

  constructor(
    public readonly bounds: WorldBounds,
    private readonly tracker: SimulationTracker
  ) {
    this.tracker.track('grid_created', {
      width: this.width,
      height: this.height
    });
  }

  public get width(): number {
    return this.bounds.width;
  }

  public get height(): number {
    return this.bounds.height;
  }

  public setCell(x: number, y: number): void {
    if (x < 0 || x >= this.width || y < 0 || y >= this.height) {

      this.tracker.track('setCell Error. Values outside the range', {
        x,
        y,
        width: this.width,
        height: this.height
      });

      throw new Error(`Coordinates out of bounds: (${x}, ${y})`);
    }

    const key = this.generateKey(x, y);
    this.cells.set(key, { x, y });
  }

  public getCell(x: number, y: number): Cell | undefined {
    return this.cells.get(this.generateKey(x, y));
  }

  public hasCell(x: number, y: number): boolean {
    return this.cells.has(this.generateKey(x, y));
  }

  public getAllCells(): Cell[] {
    return Array.from(this.cells.values());
  }

  public getBounds(): WorldBounds {
    return this.bounds;
  }

  private generateKey(x: number, y: number): string {
    return `${x},${y}`;
  }
}
