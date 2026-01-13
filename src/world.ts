import { Dimensions } from './config';
import { SimulationContext } from './simulationContext';

export interface WorldState {
  // Example state: add more as needed
  tick: number;
  totalTime: number;
  timer?: number;
}

export class World {
  public state: WorldState;
  
  constructor(
    private dimensions: Dimensions,
    public readonly context: SimulationContext
  ) {
    this.state = {
      tick: 0,
      totalTime: 0
    };
    this.context.tracker.track('world_created', { width: dimensions.width, height: dimensions.height });
  }

  get config() {
    return this.context.worldConfig;
  }

  step(time: number, delta: number) {
    this.state.tick += 1;
    this.state.totalTime += delta;
    this.state.timer = time;
    // Debounced step tracking
    this.context.tracker.track('simulation_step', { tick: this.state.tick, totalTime: this.state.totalTime }, true);
    return this.state;
  }
}
