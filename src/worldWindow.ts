import { WorldWindowConfig } from './config';
import { World } from './world';
import { SimulationContext } from './simulationContext';

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

  update(time?: number, delta?: number) {
    this.world.step(time ?? 0, delta ?? 0);
    return this.state;
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
