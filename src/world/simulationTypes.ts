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

/**
 * Enum for selecting which seasonal variation algorithm to apply
 */
export enum SeasonStrategy {
  HEMISPHERIC = 'HEMISPHERIC',
  GLOBAL_UNIFORM = 'GLOBAL_UNIFORM'
}

/**
 * Enum for controlling whether seasons transition smoothly or with discretized boundaries
 */
export enum TransitionMode {
  SMOOTH = 'SMOOTH',
  DISCRETIZED = 'DISCRETIZED'
}

/**
 * Enum for discrete season names
 */
export enum DiscreteSeasonName {
  SPRING = 'spring',
  SUMMER = 'summer',
  AUTUMN = 'autumn',
  WINTER = 'winter'
}

/**
 * Seasonal data for a specific cell at a given point in the year
 */
export interface SeasonalData {
  /** Which of the four seasons we're currently in */
  readonly discreteSeason: DiscreteSeasonName;
  /** Smooth 0–1 value for interpolation */
  readonly continuousSeasonalFactor: number;
  /** Current year progress 0–1 from TimeKeeper */
  readonly yearProgress: number;
  /** Which hemisphere or global if uniform strategy */
  readonly hemisphere: 'northern' | 'southern' | 'global';
  /** Position within transition zone (0–1), useful for ease-in/out curves */
  readonly transitionPhase: number;
}

/**
 * Context passed to layers containing all environmental and contextual data
 */
export interface LayerContext {
  /** Current seasonal information */
  readonly seasonalData: SeasonalData;
  /** Reference to time keeper for layer to query ticks/year progress */
  readonly timeKeeper: ITimeKeeper;
  /** Width of simulation grid */
  readonly gridWidth: number;
  /** Height of simulation grid */
  readonly gridHeight: number;
  /** For layers to emit their own events */
  readonly simulationTracker: any; // Using any to avoid circular imports; should be SimulationTracker
}

/**
 * Interface for season strategy implementations (strategy pattern)
 */
export interface ISeasonStrategy {
  /**
   * Computes seasonal data for a specific cell at given year progress
   * @param x cell x-coordinate
   * @param y cell y-coordinate
   * @param yearProgress 0–1 from TimeKeeper
   * @returns SeasonalData object
   */
  getSeasonForCell(x: number, y: number, yearProgress: number): SeasonalData;

  /**
   * Called at SeasonManager creation after construction
   */
  initialize(): void;
}
