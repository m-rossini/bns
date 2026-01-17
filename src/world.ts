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
    public readonly context: SimulationContext
  ) {
    this.state = {
      tick: this.context.timeKeeper.getTicks(),
      totalTime: 0
    };
    this.context.tracker.track('world_created', { 
      width: this.context.windowConfig.canvasWidth, 
      height: this.context.windowConfig.canvasHeight,
      initialTick: this.state.tick,
      yearProgress: this.context.timeKeeper.getYearProgress()
    });
  }

  step(time: number, delta: number) {
    this.context.timeKeeper.tick();
    this.state.tick = this.context.timeKeeper.getTicks();
    this.state.totalTime += delta;
    this.state.timer = time;
    
    // Debounced step tracking
    this.context.tracker.track('simulation_step', { 
      tick: this.state.tick, 
      totalTime: this.state.totalTime,
      yearProgress: this.context.timeKeeper.getYearProgress(),
      totalYears: this.context.timeKeeper.getTotalYears()
    }, true);
    return this.state;
  }
}
