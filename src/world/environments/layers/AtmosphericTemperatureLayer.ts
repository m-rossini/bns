import { IEnvironmentLayer, EnvironmentLayerType, ITimeKeeper, EnvironmentLayerState, IGrid, Cell, IEnvironment, LayerContext } from '@/world/simulationTypes';

export class AtmosphericTemperatureLayer implements IEnvironmentLayer {
  public readonly type = EnvironmentLayerType.Temperature;
  private baseTemp: number;
  private seasonalFactor: number = 0;

  constructor(
    params: { baseTemperature?: number },
    private readonly context: LayerContext
  ) {
    this.baseTemp = params.baseTemperature ?? 20;
    this.seasonalFactor = context.seasonalData.continuousSeasonalFactor;
    
    context.simulationTracker.track('layer_created', { 
      provider: 'AtmosphericTemperatureLayer',
      type: this.type,
      contextProvided: true
    });
  }

  public update(timeKeeper: ITimeKeeper, _grid: IGrid, _environment: IEnvironment): EnvironmentLayerState {
    // Update seasonal factor from context each tick
    this.seasonalFactor = this.context.seasonalData.continuousSeasonalFactor;

    this.context.simulationTracker.track('temperature_layer_updated', {
      yearProgress: this.context.timeKeeper.getYearProgress(),
      baseTemp: this.baseTemp
    }, true);

    return { yearProgress: this.context.timeKeeper.getYearProgress(), baseTemp: this.baseTemp };
  }

  public getValueAt(position: Cell): number {
    const equatorY = 20;
    const maxDeltaY = 20;
    const latitudinalFactor = 1 - (Math.abs(position.y - equatorY) / maxDeltaY);
    return this.baseTemp + (10 * this.seasonalFactor) + (5 * latitudinalFactor);
  }
}
