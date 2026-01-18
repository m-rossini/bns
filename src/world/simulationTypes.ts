export interface ITimeKeeper {
  /**
   * Increments the internal simulation ticks and returns the new value
   */
  tick(): number;

  getTicks() : number;
  /**
   * Returns a normalized value [0.0, 1.0) representing the progress within the current year.
   */
  getYearProgress(): number;

  /**
   * Returns the count of full years passed.
   */
  getTotalYears(): number;

  /**
   * Returns the configured ticks per year.
   */
  getTicksPerYear(): number;
}

export enum EnvironmentLayerType {
  Temperature = 'temperature',
  Luminosity = 'luminosity',
  SolarEnergy = 'solarEnergy',
  Humidity = 'humidity'
}

export type EnvironmentLayerState = any;
export type EnvironmentState = Record<EnvironmentLayerType, EnvironmentLayerState>;

export interface IGrid {
  readonly width: number;
  readonly height: number;
  hasCell(x: number, y: number): boolean;
  getAllCells(): Iterable<Cell>;
}

export interface IEnvironmentLayer {
  readonly type: EnvironmentLayerType;
  update(timeKeeper: ITimeKeeper, grid: IGrid, environment: IEnvironment): EnvironmentLayerState;
  getValueAt(position: Cell): number;
}

export interface IEnvironment {
  update(timeKeeper: ITimeKeeper, grid: IGrid): EnvironmentState;
  getLayer(type: EnvironmentLayerType): IEnvironmentLayer | undefined;
  getValueAt(type: EnvironmentLayerType, position: Cell): number;
}

export interface WorldState {
  // Example state: add more as needed
  tick: number;
  totalTime: number;
  timer?: number;
  environment?: EnvironmentState;
}

export interface Cell {
  readonly x: number;
  readonly y: number;
}

/**
 * Bounds for the logical simulation space.
 */
export interface WorldBounds {
  readonly width: number;  // Maximum number of cells in X
  readonly height: number; // Maximum number of cells in Y
}
