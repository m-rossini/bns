console.log("CompositeEnvironment loaded");
import { IEnvironment, IEnvironmentLayer, EnvironmentLayerType, ITimeKeeper, EnvironmentState, IGrid, Cell, SeasonStrategy, TransitionMode } from '@/world/simulationTypes';
import { logDebug } from '@/observability/logger';
import { SimulationTracker } from '@/observability/simulationTracker';
import { SeasonManager, HemisphericSeasonStrategy, GlobalUniformSeasonStrategy } from '@/world/environments/SeasonManager';
import { AtmosphericTemperatureLayer } from '@/world/environments/layers/AtmosphericTemperatureLayer';
import { HumidityLayer } from '@/world/environments/layers/HumidityLayer';
import { LuminosityLayer } from '@/world/environments/layers/LuminosityLayer';

console.log(10, "here")

export class CompositeEnvironment implements IEnvironment {
  private layers: Map<EnvironmentLayerType, IEnvironmentLayer> = new Map();
  private seasonManager: SeasonManager;

  constructor(
    layerConfigs: { type: EnvironmentLayerType, params: any }[],
    private readonly tracker: SimulationTracker,
    private readonly timeKeeper: ITimeKeeper,
    private readonly gridWidth: number,
    private readonly gridHeight: number,
    seasonStrategy: SeasonStrategy = SeasonStrategy.HEMISPHERIC,
    seasonTransitionMode: TransitionMode = TransitionMode.DISCRETIZED
  ) {
    // Initialize SeasonManager with selected strategy
    const strategy = seasonStrategy === SeasonStrategy.HEMISPHERIC
      ? new HemisphericSeasonStrategy('HEMISPHERIC', seasonTransitionMode, this.tracker)
      : new GlobalUniformSeasonStrategy('GLOBAL_UNIFORM', seasonTransitionMode, this.tracker);

    this.seasonManager = new SeasonManager(strategy, this.tracker, seasonTransitionMode);

    // Instantiate layers using private method
    layerConfigs.forEach(cfg => {
      const layer = this.createLayerWithContext(cfg.type, cfg.params);
      this.layers.set(layer.type, layer);
    });

    this.tracker.track('environment_created', {
      provider: 'CompositeEnvironment',
      layerCount: this.layers.size,
      seasonStrategy: seasonStrategy,
      seasonTransitionMode: seasonTransitionMode
    });
  }

  public update(timeKeeper: ITimeKeeper, grid: IGrid): EnvironmentState {
    // Update season manager each tick
    this.seasonManager.step(timeKeeper, this.gridWidth, this.gridHeight);

    const state: any = {};
    this.layers.forEach((layer, type) => {
      state[type] = layer.update(timeKeeper, grid, this);
    });

    this.tracker.track('environment_updated', {
      tick: timeKeeper.getTicks(),
      layerCount: this.layers.size
    }, true);

    return state as EnvironmentState;
  }

  public getLayer(type: EnvironmentLayerType): IEnvironmentLayer | undefined {
    return this.layers.get(type);
  }

  public getValueAt(type: EnvironmentLayerType, position: Cell): number {
    const layer = this.layers.get(type);
    return layer ? layer.getValueAt(position) : 0;
  }

  /**
   * Private factory method to create a layer with LayerContext from SeasonManager
   */
  private createLayerWithContext(layerType: EnvironmentLayerType, params: any = {}): IEnvironmentLayer {
    logDebug(`Creating layer of type: ${layerType}`);
    const yearProgress = this.timeKeeper.getYearProgress();
    const centerX = this.gridWidth / 2;
    const centerY = this.gridHeight / 2;

    const layerContext = this.seasonManager.createLayerContext(
      this.timeKeeper,
      this.gridWidth,
      this.gridHeight,
      yearProgress,
      centerX,
      centerY
    );

    switch (layerType) {
      case EnvironmentLayerType.Temperature:
        return new AtmosphericTemperatureLayer(params, layerContext);
      case EnvironmentLayerType.Humidity:
        return new HumidityLayer(params, layerContext);
      case EnvironmentLayerType.Luminosity:
        return new LuminosityLayer(params, layerContext);
      default:
        throw new Error(`Unknown layer type: ${layerType}`);
    }
  }

  public getSeasonManager(): SeasonManager {
    return this.seasonManager;
  }
}
