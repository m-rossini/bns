import { beforeEach, describe, expect, it, vi } from 'vitest';
import { WorldWindow } from '@/worldWindow';
import { SimulationContext } from '@/simulationContext';
import { SimulationTracker } from '@/observability/simulationTracker';
import { ITimeKeeper, IEnvironment } from '@/world/simulationTypes';
import { WorldConfig, WorldWindowConfig } from '@/config';
import { World } from '@/world/world';

describe('WorldWindow', () => {
  let worldWindow: WorldWindow;
  let gridGraphics: any;
  let world: World;

  const mockTracker = {
    track: vi.fn()
  } as unknown as SimulationTracker;

  const mockTimeKeeper = {
    getTicks: vi.fn().mockReturnValue(0),
    getYearProgress: vi.fn().mockReturnValue(0),
    getTotalYears: vi.fn().mockReturnValue(0),
    tick: vi.fn()
  } as unknown as ITimeKeeper;

  const mockEnvironment = {
    getValueAt: vi.fn().mockReturnValue(0),
    update: vi.fn()
  } as unknown as IEnvironment;

  const mockWorldConfig: WorldConfig = {
    dimensions: { width: 10, height: 10 },
    environment: { 
      provider: 'test', 
      params: {},
      layers: []
    },
    time: { provider: 'test', params: { ticksPerYear: 100 } }
  };

  const mockWindowConfig: WorldWindowConfig = {
    canvasWidth: 200,
    canvasHeight: 200,
    canvasBackgroundColor: '#e45a96',
    cellSizeInPixels: 20,
    gridColor: '#efde74',
    gridLineThickness: 1,
    gridLineAlpha: 0.7,
    gridDrawMode: 'lines'
  } as WorldWindowConfig;

  const context = new SimulationContext(mockTracker, mockWorldConfig, mockWindowConfig);

  beforeEach(() => {
    world = new World(context, mockTimeKeeper, mockEnvironment);
    worldWindow = new WorldWindow(context, world);
    gridGraphics = {
      clear: vi.fn(),
      lineStyle: vi.fn(),
      lineBetween: vi.fn(),
      fillStyle: vi.fn(),
      fillRect: vi.fn()
    } as any;
  });

  it('clears the graphics and returns early if grid is hidden', () => {
    worldWindow.state.showGrid = false;
    worldWindow.draw(gridGraphics);
    expect(gridGraphics.clear).toHaveBeenCalledTimes(1);
    expect(gridGraphics.lineStyle).not.toHaveBeenCalled();
  });

  it('draws lines when showGrid is true and mode is lines', () => {
    worldWindow.state.showGrid = true;
    // mode is 'lines' by default in mockWindowConfig
    worldWindow.draw(gridGraphics);
    expect(gridGraphics.clear).toHaveBeenCalled();
    expect(gridGraphics.lineStyle).toHaveBeenCalled();
    expect(gridGraphics.lineBetween).toHaveBeenCalled();
  });

  it('draws cells when mode is rects', () => {
    // We need to change the config, but config is readonly in real app.
    // For test, we can use a new context or just mock the property if possible.
    const rectConfig = { ...mockWindowConfig, gridDrawMode: 'rects' } as WorldWindowConfig;
    const rectContext = new SimulationContext(mockTracker, mockWorldConfig, rectConfig);
    const rectWorld = new World(rectContext, mockTimeKeeper, mockEnvironment);
    const rectWindow = new WorldWindow(rectContext, rectWorld);
    
    // Seed some cells
    rectWindow.world.grid.setCell(1, 1);
    rectWindow.world.grid.setCell(2, 2);

    rectWindow.draw(gridGraphics);
    expect(gridGraphics.clear).toHaveBeenCalled();
    // 2 background rects + 2 cell rects
    expect(gridGraphics.fillRect).toHaveBeenCalledTimes(4);
    // logical (1,1) * cellSize(20) = pixel (20,20)
    expect(gridGraphics.fillRect).toHaveBeenCalledWith(20, 20, 20, 20);
    expect(gridGraphics.fillRect).toHaveBeenCalledWith(40, 40, 20, 20);
  });
});
