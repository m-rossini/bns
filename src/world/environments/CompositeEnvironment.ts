import { IEnvironment, IEnvironmentLayer, EnvironmentLayerType, ITimeKeeper, EnvironmentState, IGrid, Cell } from '@/world/simulationTypes';
import { logDebug } from '@/observability/logger';

export class CompositeEnvironment implements IEnvironment {
  private layers: Map<EnvironmentLayerType, IEnvironmentLayer> = new Map();

  constructor(layers: IEnvironmentLayer[]) {
    layers.forEach(layer => {
      this.layers.set(layer.type, layer);
      logDebug(`Layer initialized in CompositeEnvironment: ${layer.type}`);
    });
  }

  public update(timeKeeper: ITimeKeeper, grid: IGrid): EnvironmentState {
    const state: any = {};
    this.layers.forEach((layer, type) => {
      state[type] = layer.update(timeKeeper, grid, this);
    });
    return state as EnvironmentState;
  }

  public getLayer(type: EnvironmentLayerType): IEnvironmentLayer | undefined {
    return this.layers.get(type);
  }

  public getValueAt(type: EnvironmentLayerType, position: Cell): number {
    const layer = this.layers.get(type);
    return layer ? layer.getValueAt(position) : 0;
  }
}
