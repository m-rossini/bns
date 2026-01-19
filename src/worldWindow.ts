import { WorldWindowConfig } from '@/config';
import { World } from '@/world/world';
import { SimulationContext } from '@/simulationContext';
import { EnvironmentLayerType } from '@/world/simulationTypes';
import type { GameObjects } from 'phaser';

export interface WorldWindowState {
  showGrid: boolean;
}

export class WorldWindow {
  public state: WorldWindowState;
  public readonly world: World;
  public readonly config: WorldWindowConfig;

  constructor(public readonly context: SimulationContext, world: World) {
    this.config = context.windowConfig;
    this.state = { showGrid: true };

    this.world = world;
    this.context.tracker.track('worldWindow_created', {
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
    
    this.drawBackground(graphics);

    if (!this.state.showGrid) {
      return;
    }

    if (this.config.gridDrawMode === 'rects') {
      this.drawCells(graphics);
    } else {
      this.drawLines(graphics);
    }
  }

  private drawBackground(graphics: GameObjects.Graphics): void {
    const luminosity = this.world.environment.getValueAt(EnvironmentLayerType.Luminosity, { x: 0, y: 0 });
    // Darken or lighten the background color based on luminosity
    const baseColor = this.hexToColor(this.config.canvasBackgroundColor);
    
    // Simple way to adjust brightness - this is just a placeholder to show it works
    // In a real app we'd use Phaser.Display.Color or similar
    graphics.fillStyle(baseColor, 1);
    graphics.fillRect(0, 0, this.config.canvasWidth, this.config.canvasHeight);
    
    // Overlay a dark rectangle with varying alpha based on luminosity (inverse)
    graphics.fillStyle(0x000000, Math.max(0, 0.5 * (1 - luminosity)));
    graphics.fillRect(0, 0, this.config.canvasWidth, this.config.canvasHeight);
  }

  private drawLines(graphics: GameObjects.Graphics): void {
    const step = this.config.cellSizeInPixels ?? 40;
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
    const cellSizeInPixels = this.config.cellSizeInPixels;

    for (const cell of this.world.grid.getAllCells()) {
      const screenX = cell.x * cellSizeInPixels;
      const screenY = cell.y * cellSizeInPixels;
      graphics.fillStyle(this.randomColor(), alpha);
      graphics.fillRect(screenX, screenY, cellSizeInPixels, cellSizeInPixels);
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

export async function initWorldWindow(context: SimulationContext): Promise<WorldWindow> {
  context.tracker.track('world_window_initializing', {});
  const world = await World.create(context);
  worldWindow = new WorldWindow(context, world);
  return worldWindow;
}
