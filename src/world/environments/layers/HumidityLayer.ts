import { IEnvironmentLayer, EnvironmentLayerType, ITimeKeeper, EnvironmentLayerState, IGrid, Cell, IEnvironment, LayerContext } from '@/world/simulationTypes';
import { SimulationTracker } from '@/observability/simulationTracker';

export class HumidityLayer implements IEnvironmentLayer {
  public readonly type = EnvironmentLayerType.Humidity;
  private seasonalFactor: number = 0;
  private baseHumidity: number;

  constructor(
    params: { baseHumidity?: number },
    private readonly context: LayerContext
  ) {
    this.baseHumidity = params.baseHumidity ?? 0.5;
    // Humidity inverse to temperature - peaks when seasonal factor is lower
    this.seasonalFactor = 1 - context.seasonalData.continuousSeasonalFactor;
    
    context.simulationTracker.track('layer_created', { 
      provider: 'HumidityLayer', 
      type: this.type,
      contextProvided: true
    });
  }

  public update(timeKeeper: ITimeKeeper, _grid: IGrid, _environment: IEnvironment): EnvironmentLayerState {
    // Update seasonal factor inversely from context each tick
    this.seasonalFactor = 1 - this.context.seasonalData.continuousSeasonalFactor;

    this.context.simulationTracker.track('humidity_layer_updated', {
      seasonalFactor: this.seasonalFactor,
      yearProgress: timeKeeper.getYearProgress()
    }, true);

    return { seasonalFactor: this.seasonalFactor, baseHumidity: this.baseHumidity };
  }

  public getValueAt(_position: Cell): number {
    return Math.max(0, Math.min(1, this.baseHumidity + (0.2 * this.seasonalFactor)));
  }
}
