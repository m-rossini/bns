import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CompositeEnvironment } from '@/world/environments/CompositeEnvironment';
import { AtmosphericTemperatureLayer } from '@/world/environments/layers/AtmosphericTemperatureLayer';
import { HumidityLayer } from '@/world/environments/layers/HumidityLayer';
import { LuminosityLayer } from '@/world/environments/layers/LuminosityLayer';
import { EnvironmentLayerType, SeasonStrategy, TransitionMode, LayerContext, DiscreteSeasonName } from '@/world/simulationTypes';
import { SimulationTracker } from '@/observability/simulationTracker';
import { SequentialTimeKeeper } from '@/world/time/SequentialTimeKeeper';
import { SparseGrid } from '@/world/SparseGrid';

describe('CompositeEnvironment with SeasonManager', () => {
  let mockTracker: SimulationTracker;
  let timeKeeper: SequentialTimeKeeper;
  let grid: SparseGrid;
  let environment: CompositeEnvironment;

  beforeEach(() => {
    mockTracker = {
      track: vi.fn()
    } as unknown as SimulationTracker;

    timeKeeper = new SequentialTimeKeeper({ ticksPerYear: 360, initialTicks: 0 });
    grid = new SparseGrid({ width: 60, height: 40 }, mockTracker);

    // Create a minimal LayerContext for layer construction
    const seasonalData = {
      discreteSeason: DiscreteSeasonName.SUMMER,
      continuousSeasonalFactor: 0.8,
      yearProgress: 0.5,
      hemisphere: 'northern' as const,
      transitionPhase: 0
    };

    const layerContext = Object.freeze({
      seasonalData,
      timeKeeper,
      gridWidth: 60,
      gridHeight: 40,
      simulationTracker: mockTracker
    }) as LayerContext;

    const layers = [
      new LuminosityLayer({}, layerContext),
      new AtmosphericTemperatureLayer({ baseTemperature: 20 }, layerContext),
      new HumidityLayer({ baseHumidity: 0.5 }, layerContext)
    ];

    environment = new CompositeEnvironment(
      layers,
      {},
      mockTracker,
      timeKeeper,
      60,
      40,
      SeasonStrategy.HEMISPHERIC,
      TransitionMode.DISCRETIZED
    );
  });

  describe('Initialization', () => {
    it('should create with hemispheric season strategy', () => {
      expect(environment).toBeDefined();
      expect(environment.getSeasonManager()).toBeDefined();
    });

    it('should emit environment_created event with season strategy info', () => {
      const calls = (mockTracker.track as any).mock.calls;
      const createdCall = calls.find((call: any[]) => call[0] === 'environment_created');
      expect(createdCall).toBeDefined();
      expect(createdCall[1].seasonStrategy).toBe(SeasonStrategy.HEMISPHERIC);
      expect(createdCall[1].seasonTransitionMode).toBe(TransitionMode.DISCRETIZED);
    });

    it('should initialize with correct layer count', () => {
      const calls = (mockTracker.track as any).mock.calls;
      const createdCall = calls.find((call: any[]) => call[0] === 'environment_created');
      expect(createdCall[1].layerCount).toBe(3);
    });
  });

  describe('createLayerWithContext factory method', () => {
    it('should create temperature layer with context', () => {
      const layer = environment.createLayerWithContext(EnvironmentLayerType.Temperature, { baseTemperature: 25 });
      expect(layer).toBeDefined();
      expect(layer.type).toBe(EnvironmentLayerType.Temperature);
    });

    it('should create humidity layer with context', () => {
      const layer = environment.createLayerWithContext(EnvironmentLayerType.Humidity, { baseHumidity: 0.6 });
      expect(layer).toBeDefined();
      expect(layer.type).toBe(EnvironmentLayerType.Humidity);
    });

    it('should create luminosity layer with context', () => {
      const layer = environment.createLayerWithContext(EnvironmentLayerType.Luminosity, {});
      expect(layer).toBeDefined();
      expect(layer.type).toBe(EnvironmentLayerType.Luminosity);
    });

    it('should throw error for unknown layer type', () => {
      expect(() => {
        environment.createLayerWithContext('unknown' as any);
      }).toThrow('Unknown layer type');
    });
  });

  describe('update method with season manager', () => {
    it('should call seasonManager.step during update', () => {
      const seasonManagerSpy = vi.spyOn(environment.getSeasonManager(), 'step');
      environment.update(timeKeeper, grid);
      expect(seasonManagerSpy).toHaveBeenCalledWith(timeKeeper, 60, 40);
    });

    it('should emit environment_updated event', () => {
      vi.clearAllMocks();
      environment.update(timeKeeper, grid);
      const calls = (mockTracker.track as any).mock.calls;
      const updatedCall = calls.find((call: any[]) => call[0] === 'environment_updated');
      expect(updatedCall).toBeDefined();
    });

    it('should return environment state with all layers', () => {
      const state = environment.update(timeKeeper, grid);
      expect(state).toBeDefined();
      expect(state[EnvironmentLayerType.Luminosity]).toBeDefined();
      expect(state[EnvironmentLayerType.Temperature]).toBeDefined();
      expect(state[EnvironmentLayerType.Humidity]).toBeDefined();
    });
  });

  describe('Layer retrieval', () => {
    it('should get layer by type', () => {
      const tempLayer = environment.getLayer(EnvironmentLayerType.Temperature);
      expect(tempLayer).toBeDefined();
      expect(tempLayer?.type).toBe(EnvironmentLayerType.Temperature);
    });

    it('should return undefined for non-existent layer', () => {
      const layer = environment.getLayer(EnvironmentLayerType.SolarEnergy);
      expect(layer).toBeUndefined();
    });

    it('should get value at position for specific layer type', () => {
      const value = environment.getValueAt(EnvironmentLayerType.Temperature, { x: 30, y: 20 });
      expect(value).toBeDefined();
      expect(typeof value).toBe('number');
    });

    it('should return 0 for non-existent layer type', () => {
      const value = environment.getValueAt(EnvironmentLayerType.SolarEnergy, { x: 30, y: 20 });
      expect(value).toBe(0);
    });
  });
});
