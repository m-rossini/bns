import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AtmosphericTemperatureLayer } from '@/world/environments/layers/AtmosphericTemperatureLayer';
import { HumidityLayer } from '@/world/environments/layers/HumidityLayer';
import { LuminosityLayer } from '@/world/environments/layers/LuminosityLayer';
import { LayerContext, DiscreteSeasonName } from '@/world/simulationTypes';
import { SimulationTracker } from '@/observability/simulationTracker';
import { SequentialTimeKeeper } from '@/world/time/SequentialTimeKeeper';

describe('Layers with LayerContext', () => {
  let mockTracker: SimulationTracker;
  let timeKeeper: SequentialTimeKeeper;
  let layerContext: LayerContext;

  beforeEach(() => {
    mockTracker = {
      track: vi.fn()
    } as unknown as SimulationTracker;

    timeKeeper = new SequentialTimeKeeper({ ticksPerYear: 360, initialTicks: 0 });

    // Create a minimal LayerContext
    layerContext = Object.freeze({
      seasonalData: {
        discreteSeason: DiscreteSeasonName.SUMMER,
        continuousSeasonalFactor: 0.8,
        yearProgress: 0.5,
        hemisphere: 'northern',
        transitionPhase: 0
      },
      timeKeeper,
      gridWidth: 60,
      gridHeight: 40,
      simulationTracker: mockTracker
    }) as LayerContext;
  });

  describe('AtmosphericTemperatureLayer', () => {
    it('should accept LayerContext in constructor', () => {
      const layer = new AtmosphericTemperatureLayer(
        { baseTemperature: 20 },
        layerContext
      );
      expect(layer).toBeDefined();
    });

    it('should emit layer_created event with contextProvided flag', () => {
      const layer = new AtmosphericTemperatureLayer(
        { baseTemperature: 20 },
        layerContext
      );
      const calls = (mockTracker.track as any).mock.calls;
      const createdEvent = calls.find((call: any[]) => call[0] === 'layer_created');
      expect(createdEvent).toBeDefined();
      expect(createdEvent[1].contextProvided).toBe(true);
    });

    it('should use seasonal data from context in calculations', () => {
      const layer = new AtmosphericTemperatureLayer(
        { baseTemperature: 20 },
        layerContext
      );
      const value1 = layer.getValueAt({ x: 20, y: 20 });
      
      // Create layer with different seasonal factor
      const winterContext = Object.freeze({
        ...layerContext,
        seasonalData: {
          ...layerContext.seasonalData,
          continuousSeasonalFactor: 0.1,
          discreteSeason: DiscreteSeasonName.WINTER
        }
      }) as LayerContext;
      
      const layer2 = new AtmosphericTemperatureLayer(
        { baseTemperature: 20 },
        winterContext
      );
      const value2 = layer2.getValueAt({ x: 20, y: 20 });
      
      // Summer should be warmer than winter
      expect(value1).toBeGreaterThan(value2);
    });

    it('should maintain temperature range', () => {
      const layer = new AtmosphericTemperatureLayer(
        { baseTemperature: 20 },
        layerContext
      );
      
      for (let x = 0; x < 60; x += 10) {
        for (let y = 0; y < 40; y += 10) {
          const value = layer.getValueAt({ x, y });
          expect(value).toBeGreaterThanOrEqual(-20);
          expect(value).toBeLessThanOrEqual(50);
        }
      }
    });
  });

  describe('HumidityLayer', () => {
    it('should accept LayerContext in constructor', () => {
      const layer = new HumidityLayer(
        { baseHumidity: 0.5 },
        layerContext
      );
      expect(layer).toBeDefined();
    });

    it('should emit layer_created event', () => {
      const layer = new HumidityLayer(
        { baseHumidity: 0.5 },
        layerContext
      );
      const calls = (mockTracker.track as any).mock.calls;
      const createdEvent = calls.find((call: any[]) => call[0] === 'layer_created');
      expect(createdEvent).toBeDefined();
      expect(createdEvent[1].contextProvided).toBe(true);
    });

    it('should use seasonal data from context', () => {
      const layer = new HumidityLayer(
        { baseHumidity: 0.5 },
        layerContext
      );
      const value1 = layer.getValueAt({ x: 30, y: 20 });
      
      const winterContext = Object.freeze({
        ...layerContext,
        seasonalData: {
          ...layerContext.seasonalData,
          continuousSeasonalFactor: 0.1
        }
      }) as LayerContext;
      
      const layer2 = new HumidityLayer(
        { baseHumidity: 0.5 },
        winterContext
      );
      const value2 = layer2.getValueAt({ x: 30, y: 20 });
      
      // Values should differ based on seasonal factor
      expect(value1).not.toEqual(value2);
    });
  });

  describe('LuminosityLayer', () => {
    it('should accept LayerContext in constructor', () => {
      const layer = new LuminosityLayer({}, layerContext);
      expect(layer).toBeDefined();
    });

    it('should emit layer_created event', () => {
      const layer = new LuminosityLayer({}, layerContext);
      const calls = (mockTracker.track as any).mock.calls;
      const createdEvent = calls.find((call: any[]) => call[0] === 'layer_created');
      expect(createdEvent).toBeDefined();
      expect(createdEvent[1].contextProvided).toBe(true);
    });

    it('should use seasonal data from context', () => {
      const layer = new LuminosityLayer({}, layerContext);
      const value1 = layer.getValueAt({ x: 30, y: 20 });
      
      const winterContext = Object.freeze({
        ...layerContext,
        seasonalData: {
          ...layerContext.seasonalData,
          continuousSeasonalFactor: 0.1
        }
      }) as LayerContext;
      
      const layer2 = new LuminosityLayer({}, winterContext);
      const value2 = layer2.getValueAt({ x: 30, y: 20 });
      
      // Summer should be more luminous than winter
      expect(value1).toBeGreaterThan(value2);
    });

    it('should maintain luminosity in valid range', () => {
      const layer = new LuminosityLayer({}, layerContext);
      
      for (let x = 0; x < 60; x += 10) {
        for (let y = 0; y < 40; y += 10) {
          const value = layer.getValueAt({ x, y });
          expect(value).toBeGreaterThanOrEqual(0);
          expect(value).toBeLessThanOrEqual(1);
        }
      }
    });
  });
});
