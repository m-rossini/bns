import { describe, it, expect, beforeEach } from 'vitest';
import { World } from '@/world/world';
import { SimulationContext } from '@/simulationContext';
import { SimulationTracker } from '@/observability/simulationTracker';
import { WorldConfig, WorldWindowConfig } from '@/config';
import { SequentialTimeKeeper } from '@/world/time/SequentialTimeKeeper';
import { CompositeEnvironment } from '@/world/environments/CompositeEnvironment';
import { LuminosityLayer } from '@/world/environments/layers/LuminosityLayer';
import { Event, EventSink } from '@/observability/types';
import { DiscreteSeasonName, LayerContext, SeasonStrategy, TransitionMode } from '@/world/simulationTypes';

class FakeSink implements EventSink {
  public events: Event[] = [];
  async sendEvent(event: Event): Promise<void> {
    this.events.push(event);
  }
}

describe('World', () => {
  let sink: FakeSink;
  let tracker: SimulationTracker;
  let timeKeeper: SequentialTimeKeeper;
  let context: SimulationContext;
  let world: World;

  const mockWorldConfig: WorldConfig = {
    dimensions: { width: 10, height: 10 },
    seasonStrategy: SeasonStrategy.HEMISPHERIC,
    seasonTransitionMode: TransitionMode.DISCRETIZED,
    environment: { 
      provider: 'CompositeEnvironment', 
      params: {},
      layers: [{ provider: 'LuminosityLayer', params: {} }]
    },
    time: { provider: 'SequentialTimeKeeper', params: { ticksPerYear: 100 } }
  };

  const mockWindowConfig: WorldWindowConfig = {
    canvasWidth: 200,
    canvasHeight: 200,
    cellSizeInPixels: 20,
  } as WorldWindowConfig;

  const createLayerContext = (timeKeeper: SequentialTimeKeeper): LayerContext => {
    const yearProgress = timeKeeper.getYearProgress();
    return Object.freeze({
      seasonalData: {
        discreteSeason: DiscreteSeasonName.SUMMER,
        continuousSeasonalFactor: Math.sin(yearProgress * 2 * Math.PI),
        yearProgress,
        hemisphere: 'northern',
        transitionPhase: 0
      },
      timeKeeper,
      gridWidth: 10,
      gridHeight: 10,
      simulationTracker: tracker
    }) as LayerContext;
  };

  beforeEach(() => {
    sink = new FakeSink();
    tracker = new SimulationTracker(sink, 'test-session');
    timeKeeper = new SequentialTimeKeeper({ ticksPerYear: 100 });
    const layerContext = createLayerContext(timeKeeper);
    const environment = new CompositeEnvironment(
      [new LuminosityLayer({}, layerContext)], 
      {}, 
      tracker,
      timeKeeper,
      10,
      10
    );
    context = new SimulationContext(tracker, mockWorldConfig, mockWindowConfig);
    world = new World(context, timeKeeper, environment);
  });

  it('should initialize with a grid of correct dimensions', () => {
    expect(world.grid).toBeDefined();
    expect(world.grid.width).toBe(10);
    expect(world.grid.height).toBe(10);
    
    // Check tracking (world_created is not debounced)
    const event = sink.events.find(e => e.payload.event === 'world_created');
    expect(event).toBeDefined();
    expect(event?.payload).toMatchObject({
      width: 10,
      height: 10
    });
  });

  it('should increment tick and totalTime on step', () => {
    const initialTick = world.state.tick;
    
    world.step(100, 16);
    
    expect(world.state.tick).toBe(initialTick + 1);
    expect(world.state.totalTime).toBe(16);
    expect(timeKeeper.getTicks()).toBe(initialTick + 1);
  });
});

