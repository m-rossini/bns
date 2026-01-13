import { SimulationTracker } from './observability/simulationTracker';
import { WorldConfig, WorldWindowConfig } from './config';

/**
 * SimulationContext: container for simulation-level dependencies.
 * Provides the simulation tracker and configuration to the world and its presentation.
 */
export class SimulationContext {
  constructor(
    public readonly tracker: SimulationTracker,
    public readonly worldConfig: WorldConfig,
    public readonly windowConfig: WorldWindowConfig
  ) {}
}
