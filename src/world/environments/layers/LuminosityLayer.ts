import { IEnvironmentLayer, EnvironmentLayerType, ITimeKeeper, EnvironmentLayerState, IGrid, Cell, IEnvironment, LayerContext } from '@/world/simulationTypes';

export class LuminosityLayer implements IEnvironmentLayer {
  public readonly type = EnvironmentLayerType.Luminosity;
  private seasonalFactor: number = 0;

  constructor(
    _params: any,
    private readonly context: LayerContext
  ) {
    this.seasonalFactor = context.seasonalData.continuousSeasonalFactor;
    
    context.simulationTracker.track('layer_created', { 
      provider: 'LuminosityLayer',
      type: this.type,
      contextProvided: true
    });
  }

  public update(timeKeeper: ITimeKeeper, _grid: IGrid, _environment: IEnvironment): EnvironmentLayerState {
    this.seasonalFactor = this.context.seasonalData.continuousSeasonalFactor;

    this.context.simulationTracker.track('luminosity_layer_updated', {
      yearProgress: timeKeeper.getYearProgress()
    }, true);

    return { yearProgress: timeKeeper.getYearProgress() };
  }

  public getValueAt(_position: Cell): number {
    // Luminosity directly follows seasonal factor
    return this.seasonalFactor;
  }
}
