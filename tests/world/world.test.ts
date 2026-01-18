import { describe, it, expect, vi } from 'vitest';
import { World } from '@/world/world';
import { SimulationContext } from '@/simulationContext';
import { SimulationTracker } from '@/observability/simulationTracker';
import { ITimeKeeper } from '@/world/simulationTypes';
import { WorldConfig, WorldWindowConfig } from '@/config';

describe('World', () => {
  const mockTracker = {
    track: vi.fn()
  } as unknown as SimulationTracker;

  const mockTimeKeeper = {
    getTicks: vi.fn().mockReturnValue(0),
    getYearProgress: vi.fn().mockReturnValue(0),
    getTotalYears: vi.fn().mockReturnValue(0),
    tick: vi.fn().mockImplementation(() => {
      mockTimeKeeper.getTicks = vi.fn().mockReturnValue(1);
    })
  } as unknown as ITimeKeeper;

  const mockWorldConfig: WorldConfig = {
    dimensions: { width: 10, height: 10 },
    time: { provider: 'test', params: { ticksPerYear: 100 } }
  };

  const mockWindowConfig: WorldWindowConfig = {
    canvasWidth: 200,
    canvasHeight: 200,
    cellSize: 20,
    // ... other props
  } as WorldWindowConfig;

  const context = new SimulationContext(mockTracker, mockTimeKeeper, mockWorldConfig, mockWindowConfig);

  it('should initialize with a grid of correct dimensions', () => {
    const world = new World(context);
    expect(world.grid).toBeDefined();
    expect(world.grid.width).toBe(10);
    expect(world.grid.height).toBe(10);
    expect(mockTracker.track).toHaveBeenCalledWith('world_created', expect.objectContaining({
      width: 10,
      height: 10
    }));
  });

  it('should increment tick and totalTime on step', () => {
    const world = new World(context);
    const initialTick = world.state.tick;
    
    world.step(100, 16);
    
    expect(world.state.tick).toBe(initialTick + 1);
    expect(world.state.totalTime).toBe(16);
    expect(mockTimeKeeper.tick).toHaveBeenCalled();
  });
});
