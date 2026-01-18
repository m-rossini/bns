import { IEnvironmentLayer, EnvironmentLayerType, ITimeKeeper, EnvironmentLayerState, IGrid, Cell, IEnvironment } from '@/world/simulationTypes';
import { SimulationTracker } from '@/observability/simulationTracker';

export class AtmosphericTemperatureLayer implements IEnvironmentLayer {
  public readonly type = EnvironmentLayerType.Temperature;
  private yearProgress: number = 0;
  private baseTemp: number;

  constructor(
    params: { baseTemperature: number },
    private readonly tracker: SimulationTracker
  ) {
    this.baseTemp = params.baseTemperature ?? 20;
    this.tracker.track('layer_created', { 
      provider: 'AtmosphericTemperatureLayer',
      type: this.type 
    });
  }

  public update(timeKeeper: ITimeKeeper, _grid: IGrid, _environment: IEnvironment): EnvironmentLayerState {
    this.yearProgress = timeKeeper.getYearProgress();

    this.tracker.track('temperature_layer_updated', {
      yearProgress: this.yearProgress,
      baseTemp: this.baseTemp
    }, true);

    return { yearProgress: this.yearProgress, baseTemp: this.baseTemp };
  }

  public getValueAt(position: Cell): number {
    const seasonalFactor = Math.sin(this.yearProgress * Math.PI);
    const equatorY = 20;
    const maxDeltaY = 20;
    const latitudinalFactor = 1 - (Math.abs(position.y - equatorY) / maxDeltaY);
    return this.baseTemp + (10 * seasonalFactor) + (5 * latitudinalFactor);
  }
}
