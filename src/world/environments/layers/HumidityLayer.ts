import { IEnvironmentLayer, EnvironmentLayerType, ITimeKeeper, EnvironmentLayerState, IGrid, Cell, IEnvironment } from '@/world/simulationTypes';

export class HumidityLayer implements IEnvironmentLayer {
  public readonly type = EnvironmentLayerType.Humidity;
  private seasonalFactor: number = 0;
  private baseHumidity: number;

  constructor(params: { baseHumidity: number }) {
    this.baseHumidity = params.baseHumidity ?? 0.5;
  }

  public update(timeKeeper: ITimeKeeper, _grid: IGrid, _environment: IEnvironment): EnvironmentLayerState {
    // Humidity peaks when seasonal heat is lower (sin(progress * pi) is heat)
    // So 1 - sin(progress * pi)
    this.seasonalFactor = 1 - Math.sin(timeKeeper.getYearProgress() * Math.PI);
    return { seasonalFactor: this.seasonalFactor, baseHumidity: this.baseHumidity };
  }

  public getValueAt(_position: Cell): number {
    return Math.max(0, Math.min(1, this.baseHumidity + (0.2 * this.seasonalFactor)));
  }
}
