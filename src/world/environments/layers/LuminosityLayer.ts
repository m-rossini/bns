import { IEnvironmentLayer, EnvironmentLayerType, ITimeKeeper, EnvironmentLayerState, IGrid, Cell, IEnvironment } from '@/world/simulationTypes';

export class LuminosityLayer implements IEnvironmentLayer {
  public readonly type = EnvironmentLayerType.Luminosity;
  private yearProgress: number = 0;

  constructor(_params: any) {}

  public update(timeKeeper: ITimeKeeper, _grid: IGrid, _environment: IEnvironment): EnvironmentLayerState {
    this.yearProgress = timeKeeper.getYearProgress();
    return { yearProgress: this.yearProgress };
  }

  public getValueAt(_position: Cell): number {
    // Basic seasonal factor peaking at mid-year (0.5)
    return Math.sin(this.yearProgress * Math.PI);
  }
}
