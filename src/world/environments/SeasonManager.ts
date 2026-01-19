import { ISeasonStrategy, SeasonStrategy, TransitionMode, DiscreteSeasonName, SeasonalData, LayerContext, ITimeKeeper } from '@/world/simulationTypes';
import { SimulationTracker } from '@/observability/simulationTracker';

/**
 * Strategy for hemispheric seasonal variation
 */
export class HemisphericSeasonStrategy implements ISeasonStrategy {
  constructor(
    private readonly strategyName: string,
    private readonly transitionMode: TransitionMode,
    private readonly tracker: SimulationTracker
  ) {}

  public initialize(): void {
    this.tracker.track('season_strategy_initialized', {
      strategy: this.strategyName
    });
  }

  public getSeasonForCell(x: number, y: number, yearProgress: number): SeasonalData {
    // Determine hemisphere based on y-coordinate
    // Assuming grid height is around 40, with y=0 as north pole, y=20 as equator, y=40 as south pole
    const gridHeight = 40; // This will be passed through in real implementation
    const hemisphere = this.getHemisphereForY(y, gridHeight);

    // Calculate seasonal factor based on hemisphere
    const northernFactor = Math.sin(yearProgress * 2 * Math.PI);
    const southernFactor = Math.sin((yearProgress + 0.5) * 2 * Math.PI);

    // Blend based on latitude position
    const latitudeRatio = (y - gridHeight / 2) / (gridHeight / 2);
    const blendedFactor = this.blendFactors(northernFactor, southernFactor, latitudeRatio, hemisphere);

    // Determine discrete season
    const discreteSeason = this.getDiscreteSeasonFromProgress(yearProgress, hemisphere);

    // Calculate transition phase (position within transition zone)
    const transitionPhase = this.getTransitionPhase(yearProgress);

    return {
      discreteSeason,
      continuousSeasonalFactor: (blendedFactor + 1) / 2, // Normalize from [-1, 1] to [0, 1]
      yearProgress,
      hemisphere,
      transitionPhase
    };
  }

  private getHemisphereForY(y: number, gridHeight: number): 'northern' | 'southern' | 'global' {
    const equator = gridHeight / 2;
    if (Math.abs(y - equator) < 2) {
      return 'northern'; // Equator biased to northern
    }
    return y < equator ? 'northern' : 'southern';
  }

  private blendFactors(
    northernFactor: number,
    southernFactor: number,
    latitudeRatio: number,
    hemisphere: string
  ): number {
    if (hemisphere === 'southern') {
      return southernFactor;
    }
    // At equator, blend both; at north pole, use northern
    const blendWeight = Math.abs(latitudeRatio); // 0 at equator, 1 at poles
    return northernFactor * blendWeight + southernFactor * (1 - blendWeight);
  }

  private getDiscreteSeasonFromProgress(yearProgress: number, hemisphere: string): DiscreteSeasonName {
    // Normalize to 0-1 range
    const normalized = ((yearProgress % 1) + 1) % 1;

    // Define season windows (as fractions of year)
    let seasonProgress: number;
    if (hemisphere === 'southern') {
      // Offset southern hemisphere by 0.5 (half year)
      seasonProgress = (normalized + 0.5) % 1;
    } else {
      seasonProgress = normalized;
    }

    // Season windows: Spring 0-0.25, Summer 0.25-0.5, Autumn 0.5-0.75, Winter 0.75-1.0
    // Adjusted: Winter at start (0.75-1.0 and 0-0.25)
    if (seasonProgress >= 0.75 || seasonProgress < 0.25) {
      return DiscreteSeasonName.WINTER;
    } else if (seasonProgress < 0.5) {
      return DiscreteSeasonName.SPRING;
    } else if (seasonProgress < 0.75) {
      return DiscreteSeasonName.SUMMER;
    } else {
      return DiscreteSeasonName.AUTUMN;
    }
  }

  private getTransitionPhase(yearProgress: number): number {
    // Transition zone width: ±0.05 around each boundary
    const zoneWidth = 0.05;
    const normalized = ((yearProgress % 1) + 1) % 1;

    // Check distance to nearest season boundary (0.0, 0.25, 0.5, 0.75)
    const boundaries = [0.0, 0.25, 0.5, 0.75];
    let minDistance = Infinity;

    for (const boundary of boundaries) {
      let distance = Math.abs(normalized - boundary);
      // Handle wrap-around at 0.0/1.0
      distance = Math.min(distance, Math.abs(distance - 1.0));
      minDistance = Math.min(minDistance, distance);
    }

    // If within zone, calculate phase as 0-1 across the zone
    if (minDistance <= 0.05) {
      return minDistance / 0.05;
    }
    return 0;
  }
}

/**
 * Strategy for global uniform seasonal variation
 */
export class GlobalUniformSeasonStrategy implements ISeasonStrategy {
  constructor(
    private readonly strategyName: string,
    private readonly transitionMode: TransitionMode,
    private readonly tracker: SimulationTracker
  ) {}

  public initialize(): void {
    this.tracker.track('season_strategy_initialized', {
      strategy: this.strategyName
    });
  }

  public getSeasonForCell(_x: number, _y: number, yearProgress: number): SeasonalData {
    // Apply same seasonal curve globally, ignoring coordinates
    const seasonalFactor = Math.sin(yearProgress * 2 * Math.PI);
    const discreteSeason = this.getDiscreteSeasonFromProgress(yearProgress);
    const transitionPhase = this.getTransitionPhase(yearProgress);

    return {
      discreteSeason,
      continuousSeasonalFactor: Math.max(0, Math.min(1, (seasonalFactor + 1) / 2)),
      yearProgress,
      hemisphere: 'global',
      transitionPhase
    };
  }

  private getDiscreteSeasonFromProgress(yearProgress: number): DiscreteSeasonName {
    const normalized = ((yearProgress % 1) + 1) % 1;

    // Season windows: Winter 0.75-1.0 and 0-0.25, Spring 0.25-0.5, Summer 0.5-0.75, Autumn 0.75-1.0 (adjusted)
    if (normalized >= 0.75 || normalized < 0.25) {
      return DiscreteSeasonName.WINTER;
    } else if (normalized < 0.5) {
      return DiscreteSeasonName.SPRING;
    } else if (normalized < 0.75) {
      return DiscreteSeasonName.SUMMER;
    } else {
      return DiscreteSeasonName.AUTUMN;
    }
  }

  private getTransitionPhase(yearProgress: number): number {
    const zoneWidth = 0.05;
    const normalized = ((yearProgress % 1) + 1) % 1;
    const boundaries = [0.0, 0.25, 0.5, 0.75];
    let minDistance = Infinity;

    for (const boundary of boundaries) {
      let distance = Math.abs(normalized - boundary);
      distance = Math.min(distance, Math.abs(distance - 1.0));
      minDistance = Math.min(minDistance, distance);
    }

    if (minDistance <= 0.05) {
      return minDistance / 0.05;
    }
    return 0;
  }
}

/**
 * Manages seasonal variations and distributes seasonal context to layers
 */
export class SeasonManager {
  private lastDiscreteSeasonCache: Map<string, DiscreteSeasonName>;
  private strategyName: string;

  constructor(
    private readonly strategy: ISeasonStrategy,
    private readonly tracker: SimulationTracker,
    private readonly transitionMode: TransitionMode
  ) {
    this.lastDiscreteSeasonCache = new Map();
    this.strategyName = (this.strategy.constructor as any).name;
    this.strategy.initialize();

    this.tracker.track('season_manager_created', {
      strategy: this.strategyName,
      transitionMode: transitionMode
    });
  }

  /**
   * Computes seasonal data for a specific cell at given year progress
   * Detects season boundary crossings and emits events
   */
  public getSeasonForCell(x: number, y: number, yearProgress: number): SeasonalData {
    const seasonalData = this.strategy.getSeasonForCell(x, y, yearProgress);

    // Detect season boundary crossing
    const cacheKey = seasonalData.hemisphere;
    const lastSeason = this.lastDiscreteSeasonCache.get(cacheKey);

    if (lastSeason && lastSeason !== seasonalData.discreteSeason) {
      this.tracker.track('season_boundary_crossed', {
        hemisphere: seasonalData.hemisphere,
        newSeason: seasonalData.discreteSeason,
        yearProgress: yearProgress,
        tick: Math.round(yearProgress * 360) // Approximation for now
      });
    }

    this.lastDiscreteSeasonCache.set(cacheKey, seasonalData.discreteSeason);

    return seasonalData;
  }

  /**
   * Creates a LayerContext for passing to layers
   */
  public createLayerContext(
    timeKeeper: ITimeKeeper,
    gridWidth: number,
    gridHeight: number,
    yearProgress: number,
    x: number,
    y: number
  ): LayerContext {
    const seasonalData = this.getSeasonForCell(x, y, yearProgress);

    return Object.freeze({
      seasonalData,
      timeKeeper,
      gridWidth,
      gridHeight,
      simulationTracker: this.tracker
    }) as LayerContext;
  }

  /**
   * Called by CompositeEnvironment each tick
   * Queries season for representative cells to trigger season-change event detection
   */
  public step(timeKeeper: ITimeKeeper, gridWidth: number, gridHeight: number): void {
    // Query representative cells (equator for hemispheric strategy)
    const equatorY = gridHeight / 2;
    const centerX = gridWidth / 2;
    const yearProgress = timeKeeper.getYearProgress();

    // Query both north and south for hemispheric strategy to detect boundary crossings
    this.getSeasonForCell(centerX, 0, yearProgress); // North pole
    this.getSeasonForCell(centerX, equatorY, yearProgress); // Equator
    this.getSeasonForCell(centerX, gridHeight - 1, yearProgress); // South pole
  }
}
