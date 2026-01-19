import { WorldBounds } from '@/world/simulationTypes';

export interface Dimensions {
  width: number;
  height: number;
}


function deepFreeze<T>(obj: T): T {
  Object.freeze(obj);
  Object.getOwnPropertyNames(obj).forEach((prop) => {
    const value = (obj as any)[prop];
    if (value && typeof value === 'object' && !Object.isFrozen(value)) {
      deepFreeze(value);
    }
  });
  return obj;
}

export type GridDrawMode = 'lines' | 'rects';

export interface LayerConfig {
  readonly provider: string;
  readonly params: Record<string, any>;
}

export interface WorldConfig {
  readonly dimensions: WorldBounds;
  readonly environment: {
    readonly provider: string;
    readonly layers: LayerConfig[];
    readonly params: Record<string, any>;
  };
  readonly time: {
    readonly provider: string;
    readonly params: {
      readonly ticksPerYear: number;
      readonly initialTicks?: number;
    };
  };
}

export interface WorldWindowConfig { 
  readonly canvasWidth: number;
  readonly canvasHeight: number;
  readonly canvasBackgroundColor: string;
  readonly gridColor: string;
  readonly gridLineThickness: number;
  readonly gridLineAlpha: number;
  readonly defaultFontFamily: string;
  readonly gridDrawMode: GridDrawMode;
  readonly cellSizeInPixels: number;
  // Add more drawing/presentation config here
}

export const worldConfig: Readonly<WorldConfig> = deepFreeze({
  dimensions: {
    width: 60,  // 1200 / 20
    height: 40  // 800 / 20
  },
  environment: {
    provider: 'CompositeEnvironment',
    params: {},
    layers: [
      {
        provider: 'LuminosityLayer',
        params: {}
      },
      {
        provider: 'AtmosphericTemperatureLayer',
        params: { baseTemperature: 20 }
      },
      {
        provider: 'HumidityLayer',
        params: { baseHumidity: 0.5 }
      }
    ]
  },
  time: {
    provider: 'SequentialTimeKeeper',
    params: {
      ticksPerYear: 360,
      initialTicks: 0
    }
  }
});

export const worldWindowConfig: Readonly<WorldWindowConfig> = deepFreeze({
  canvasWidth: 1200,
  canvasHeight: 800,
  canvasBackgroundColor: '#e45a96',
  gridColor: '#efde74',
  gridLineThickness: 0.5,
  gridLineAlpha: 0.7,
  defaultFontFamily: 'Arial',
  gridDrawMode: 'lines',
  cellSizeInPixels: 20
  // Add more drawing/presentation config here
});
