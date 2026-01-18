import { WorldWindowConfig } from '@/config';
import { World } from '@/world/world';
import { SimulationContext } from '@/simulationContext';
import type { GameObjects } from 'phaser';

export interface WorldWindowState {
  showGrid: boolean;
}

export class WorldWindow {
  public state: WorldWindowState;
  public readonly world: World;
  public readonly config: WorldWindowConfig;

  constructor(public readonly context: SimulationContext) {
    this.config = context.windowConfig;
    this.state = { showGrid: true };

    this.world = new World(context);
    this.context.tracker.track('simulation_start', {
      canvasWidth: this.config.canvasWidth,
      canvasHeight: this.config.canvasHeight
    });
  }

  public update(time?: number, delta?: number) {
    this.world.step(time ?? 0, delta ?? 0);
    return this.state;
  }

  public draw(graphics: GameObjects.Graphics): void {
    graphics.clear();
    if (!this.state.showGrid) {
      return;
    }

    if (this.config.gridDrawMode === 'rects') {
      this.drawCells(graphics);
    } else {
      this.drawLines(graphics);
    }
  }

  private drawLines(graphics: GameObjects.Graphics): void {
    const step = this.config.cellSize ?? 40;
    const alpha = this.config.gridLineAlpha ?? 0.7;
    const thickness = this.config.gridLineThickness ?? 1;

    graphics.lineStyle(
      thickness,
      this.hexToColor(this.config.gridColor),
      alpha
    );

    for (let x = 0; x <= this.config.canvasWidth; x += step) {
      graphics.lineBetween(x, 0, x, this.config.canvasHeight);
    }
    for (let y = 0; y <= this.config.canvasHeight; y += step) {
      graphics.lineBetween(0, y, this.config.canvasWidth, y);
    }
  }

  private drawCells(graphics: GameObjects.Graphics): void {
    const alpha = this.config.gridLineAlpha ?? 0.7;
    const cellSize = this.config.cellSize;

    for (const cell of this.world.grid.getAllCells()) {
      const screenX = cell.x * cellSize;
      const screenY = cell.y * cellSize;
      graphics.fillStyle(this.randomColor(), alpha);
      graphics.fillRect(screenX, screenY, cellSize, cellSize);
    }
  }

  private randomColor(): number {
    return Math.floor(Math.random() * 0xffffff);
  }

  private hexToColor(hex: string): number {
    const normalized = hex.replace(/^#/, '');
    return Number.parseInt(normalized, 16);
  }
}

/**
 * Global instance of WorldWindow. 
 * Must be initialized using SimulationContext during application bootstrap.
 */
export let worldWindow: WorldWindow;

export function initWorldWindow(context: SimulationContext): WorldWindow {
  worldWindow = new WorldWindow(context);
  return worldWindow;
}
