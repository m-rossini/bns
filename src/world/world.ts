import { SimulationContext } from '@/simulationContext';
import { WorldState } from '@/world/simulationTypes';
import { SparseGrid } from '@/world/SparseGrid';

export class World {
  public state: WorldState;
  public readonly grid: SparseGrid;
  
  constructor(
    public readonly context: SimulationContext
  ) {
    this.grid = new SparseGrid(this.context.worldConfig.dimensions);
    this.state = {
      tick: this.context.timeKeeper.getTicks(),
      totalTime: 0,
      environment: this.context.environment.update(this.context.timeKeeper, this.grid)
    };
    this.context.tracker.track('world_created', { 
      width: this.grid.width,
      height: this.grid.height,
      canvasWidth: this.context.windowConfig.canvasWidth, 
      canvasHeight: this.context.windowConfig.canvasHeight,
      initialTick: this.state.tick,
      yearProgress: this.context.timeKeeper.getYearProgress()
    });
  }

  step(time: number, delta: number) {
    this.state.tick = this.context.timeKeeper.tick();
    this.state.environment = this.context.environment.update(this.context.timeKeeper, this.grid);
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
