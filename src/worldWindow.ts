// worldWindow singleton: manages drawing state and presentation config
import { worldWindowConfig, Dimensions } from './config';
import { World } from './world';

export interface WorldWindowState {
  showGrid: boolean;
}

class WorldWindow {
  private static _instance: WorldWindow;
  public readonly config = worldWindowConfig;
  public state: WorldWindowState;
  public readonly world: World;

  private constructor() {
    this.state = { showGrid: true };
    const physicalWorld: Dimensions = {
        width : this.config.canvasWidth,
        height : this.config.canvasHeight
      }

    this.world = new World(physicalWorld);
  }

  static get instance(): WorldWindow {
    if (!WorldWindow._instance) {
      WorldWindow._instance = new WorldWindow();
    }
    return WorldWindow._instance;
  }

  update(time?: number, delta?: number) {
    this.world.step(time ?? 0, delta ?? 0);
    return this.state;
  }

}

export const worldWindow = WorldWindow.instance;
