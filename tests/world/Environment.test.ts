import { describe, it, expect, vi } from 'vitest';
import { CompositeEnvironment } from '@/world/environments/CompositeEnvironment';
import { LuminosityLayer } from '@/world/environments/layers/LuminosityLayer';
import { AtmosphericTemperatureLayer } from '@/world/environments/layers/AtmosphericTemperatureLayer';
import { SequentialTimeKeeper } from '@/world/time/SequentialTimeKeeper';
import { SparseGrid } from '@/world/SparseGrid';
import { EnvironmentLayerType } from '@/world/simulationTypes';
import { SimulationTracker } from '@/observability/simulationTracker';

describe('CompositeEnvironment', () => {
  const mockTracker = {
    track: vi.fn()
  } as unknown as SimulationTracker;

  const getTK = (ticks: number) => {
    const tk = new SequentialTimeKeeper({ ticksPerYear: 360 });
    for (let i = 0; i < ticks; i++) tk.tick();
    return tk;
  };

  const createEnv = () => {
    const lum = new LuminosityLayer({}, mockTracker);
    const temp = new AtmosphericTemperatureLayer({ baseTemperature: 20 }, mockTracker);
    return new CompositeEnvironment([lum, temp], {}, mockTracker);
  };

  const mockGrid = new SparseGrid({ width: 10, height: 10 }, mockTracker);

  it('should calculate luminosity based on seasonal progress from LuminosityLayer', () => {
    const env = createEnv();
    
    // Start of year (progress 0)
    env.update(getTK(0), mockGrid);
    const lumStart = env.getValueAt(EnvironmentLayerType.Luminosity, { x: 0, y: 0 });
    
    // Mid year (progress 0.5)
    env.update(getTK(180), mockGrid);
    const lumMid = env.getValueAt(EnvironmentLayerType.Luminosity, { x: 0, y: 0 });
    
    expect(lumMid).toBeGreaterThan(lumStart);
  });

  it('should vary temperature spatially from TemperatureLayer', () => {
    const env = createEnv();
    env.update(getTK(180), mockGrid);
    
    const tempEquator = env.getValueAt(EnvironmentLayerType.Temperature, { x: 0, y: 20 }); // Mid Y
    const tempPole = env.getValueAt(EnvironmentLayerType.Temperature, { x: 0, y: 0 }); // Top Y
    
    expect(tempEquator).toBeGreaterThan(tempPole);
  });

  it('should return environment state on update', () => {
    const env = createEnv();
    const state = env.update(getTK(180), mockGrid);
    
    expect(state).toBeDefined();
    expect(state[EnvironmentLayerType.Luminosity]).toBeDefined();
    expect(state[EnvironmentLayerType.Luminosity].yearProgress).toBe(0.5);
    expect(state[EnvironmentLayerType.Temperature]).toBeDefined();
  });
});
