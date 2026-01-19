import { SimulationContext } from '@/simulationContext';
import { WorldState, ITimeKeeper, IEnvironment, IEnvironmentLayer } from '@/world/simulationTypes';
import { SparseGrid } from '@/world/SparseGrid';
import { logDebug, logError } from '@/observability/logger';
import { WorldConfig } from '@/config';
import { SimulationTracker } from '@/observability/simulationTracker';

export class World {
  public state: WorldState;
  public readonly grid: SparseGrid;
  public readonly timeKeeper: ITimeKeeper;
  public readonly environment: IEnvironment;
  
  constructor(
    public readonly context: SimulationContext,
    timeKeeper: ITimeKeeper,
    environment: IEnvironment
  ) {
    this.timeKeeper = timeKeeper;
    this.environment = environment;
    this.grid = new SparseGrid(this.context.worldConfig.dimensions, this.context.tracker);
    
    this.state = {
      tick: this.timeKeeper.getTicks(),
      totalTime: 0,
      environment: this.environment.update(this.timeKeeper, this.grid)
    };
    this.context.tracker.track('world_created', { 
      width: this.grid.width,
      height: this.grid.height,
      canvasWidth: this.context.windowConfig.canvasWidth, 
      canvasHeight: this.context.windowConfig.canvasHeight,
      initialTick: this.state.tick,
      yearProgress: this.timeKeeper.getYearProgress()
    });
  }

  /**
   * Static factory method to asynchronously resolve dependencies and create a World instance.
   */
  public static async create(context: SimulationContext): Promise<World> {
    context.tracker.track('simulation_resolution_started', {
      timeProvider: context.worldConfig.time.provider,
      envProvider: context.worldConfig.environment.provider
    });

    const timeKeeper = await World.resolveTimeKeeper(context.worldConfig.time, context.tracker);
    const environment = await World.resolveEnvironment(context.worldConfig.environment, context.tracker);
    const instance = new World(context, timeKeeper, environment);

    return instance;
  }

  private static async resolveTimeKeeper(config: WorldConfig['time'], tracker: SimulationTracker): Promise<ITimeKeeper> {
    const { provider, params } = config;
    try {
      logDebug(`Resolving TimeKeeper provider: ${provider}`);
      const module = await import(`./time/${provider}.ts`);
      const TimeKeeperClass = module[provider];
      if (!TimeKeeperClass) throw new Error(`Class ${provider} not found`);
      const instance = new TimeKeeperClass(params);
      
      tracker.track('timekeeper_resolved', { provider, params });

      return instance;

    } catch (err) {
      logError(`Failed to load TimeKeeper [${provider}]`, err);
      throw err;
    }
  }

  private static async resolveEnvironment(config: WorldConfig['environment'], tracker: SimulationTracker): Promise<IEnvironment> {
    const { provider, layers: layerConfigs, params } = config;
    try {
      logDebug(`Resolving Environment provider: ${provider}`);
      const resolvedLayers: IEnvironmentLayer[] = [];
      for (const lc of layerConfigs) {
        logDebug(`Resolving Environment Layer: ${lc.provider}`);
        const lModule = await import(`./environments/layers/${lc.provider}.ts`);
        const LayerClass = lModule[lc.provider];
        if (!LayerClass) throw new Error(`Class ${lc.provider} not found`);
        resolvedLayers.push(new LayerClass(lc.params, tracker));
      }
      const module = await import(`./environments/${provider}.ts`);
      const EnvironmentClass = module[provider];
      if (!EnvironmentClass) throw new Error(`Class ${provider} not found`);
      
      const instance = new EnvironmentClass(resolvedLayers, params, tracker);
      return instance;

    } catch (err) {
      logError(`Failed to load Environment [${provider}]`, err);
      throw err;
    }
  }

  step(time: number, delta: number) {
    this.state.tick = this.timeKeeper.tick();
    this.state.environment = this.environment.update(this.timeKeeper, this.grid);
    this.state.totalTime += delta;
    this.state.timer = time;
    
    // Debounced step tracking
    this.context.tracker.track('simulation_step', { 
      tick: this.state.tick, 
      totalTime: this.state.totalTime,
      yearProgress: this.timeKeeper.getYearProgress(),
      totalYears: this.timeKeeper.getTotalYears()
    }, true);
    return this.state;
  }
}
