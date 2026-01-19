import { IEnvironmentLayer, EnvironmentLayerType, ITimeKeeper, EnvironmentLayerState, IGrid, Cell, IEnvironment } from '@/world/simulationTypes';
import { SimulationTracker } from '@/observability/simulationTracker';

export class LuminosityLayer implements IEnvironmentLayer {
  public readonly type = EnvironmentLayerType.Luminosity;
  private yearProgress: number = 0;

  constructor(
    _params: any,
    private readonly tracker: SimulationTracker
  ) {
    this.tracker.track('layer_created', { 
      provider: 'LuminosityLayer',
      type: this.type 
    });
  }

  public update(timeKeeper: ITimeKeeper, _grid: IGrid, _environment: IEnvironment): EnvironmentLayerState {
    this.yearProgress = timeKeeper.getYearProgress();

    this.tracker.track('luminosity_layer_updated', {
      yearProgress: this.yearProgress
    }, true);

    return { yearProgress: this.yearProgress };
  }

  public getValueAt(_position: Cell): number {
    // Basic seasonal factor peaking at mid-year (0.5)
    return Math.sin(this.yearProgress * Math.PI);
  }
}
