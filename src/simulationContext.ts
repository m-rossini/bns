import { SimulationTracker } from '@/observability/simulationTracker';
import { WorldConfig, WorldWindowConfig } from '@/config';
import { ITimeKeeper } from '@/world/simulationTypes';

/**
 * SimulationContext: container for simulation-level dependencies.
 * Provides the simulation tracker, time keeper, and configuration to the world and its presentation.
 */
export class SimulationContext {
  constructor(
    public readonly tracker: SimulationTracker,
    public readonly timeKeeper: ITimeKeeper,
    public readonly worldConfig: WorldConfig,
    public readonly windowConfig: WorldWindowConfig
  ) {}
}
