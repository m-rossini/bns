import { beforeEach, describe, expect, it, vi } from 'vitest';
import { WorldWindow } from '@/worldWindow';
import { SimulationContext } from '@/simulationContext';
import { SimulationTracker } from '@/observability/simulationTracker';
import { ITimeKeeper } from '@/world/simulationTypes';
import { WorldConfig, WorldWindowConfig } from '@/config';

describe('WorldWindow', () => {
  let worldWindow: WorldWindow;
  let gridGraphics: any;

  const mockTracker = {
    track: vi.fn()
  } as unknown as SimulationTracker;

  const mockTimeKeeper = {
    getTicks: vi.fn().mockReturnValue(0),
    getYearProgress: vi.fn().mockReturnValue(0),
    getTotalYears: vi.fn().mockReturnValue(0),
    tick: vi.fn()
  } as unknown as ITimeKeeper;

  const mockWorldConfig: WorldConfig = {
    dimensions: { width: 10, height: 10 },
    time: { provider: 'test', params: { ticksPerYear: 100 } }
  };

  const mockWindowConfig: WorldWindowConfig = {
    canvasWidth: 200,
    canvasHeight: 200,
    cellSize: 20,
    gridColor: '#efde74',
    gridLineThickness: 1,
    gridLineAlpha: 0.7,
    gridDrawMode: 'lines'
  } as WorldWindowConfig;

  const context = new SimulationContext(mockTracker, mockTimeKeeper, mockWorldConfig, mockWindowConfig);

  beforeEach(() => {
    worldWindow = new WorldWindow(context);
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
    const rectContext = new SimulationContext(mockTracker, mockTimeKeeper, mockWorldConfig, rectConfig);
    const rectWindow = new WorldWindow(rectContext);
    
    // Seed some cells
    rectWindow.world.grid.setCell(1, 1);
    rectWindow.world.grid.setCell(2, 2);

    rectWindow.draw(gridGraphics);
    expect(gridGraphics.clear).toHaveBeenCalled();
    expect(gridGraphics.fillRect).toHaveBeenCalledTimes(2);
    // logical (1,1) * cellSize(20) = pixel (20,20)
    expect(gridGraphics.fillRect).toHaveBeenCalledWith(20, 20, 20, 20);
    expect(gridGraphics.fillRect).toHaveBeenCalledWith(40, 40, 20, 20);
  });
});
