import { IEnvironmentLayer, EnvironmentLayerType, ITimeKeeper, EnvironmentLayerState, IGrid, Cell, IEnvironment } from '@/world/simulationTypes';

export class AtmosphericTemperatureLayer implements IEnvironmentLayer {
  public readonly type = EnvironmentLayerType.Temperature;
  private yearProgress: number = 0;
  private baseTemp: number;

  constructor(params: { baseTemperature: number }) {
    this.baseTemp = params.baseTemperature ?? 20;
  }

  public update(timeKeeper: ITimeKeeper, _grid: IGrid, _environment: IEnvironment): EnvironmentLayerState {
    this.yearProgress = timeKeeper.getYearProgress();
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
