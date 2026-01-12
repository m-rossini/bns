export interface Dimensions {
  width: number;
  height: number;
}


// Utility to deeply freeze an object (for immutability)
// EventType enum and Event interface for event tracking system
// export enum EventType {
//   UX_ACTION = "ux_action",
//   SIMULATION_EVENT = "simulation_event"
// }

// export interface Event {
//   id: string; // UUID
//   timestamp: string; // ISO string
//   eventType: EventType;
//   userId?: string;
//   sessionId?: string;
//   payload: Record<string, unknown>;
// }

// Utility to deeply freeze an object (for immutability)
function deepFreeze<T>(obj: T): T {
  Object.freeze(obj);
  Object.getOwnPropertyNames(obj).forEach((prop) => {
    // @ts-ignore
    if (obj[prop] && typeof obj[prop] === 'object' && !Object.isFrozen(obj[prop])) {
      // @ts-ignore
      deepFreeze(obj[prop]);
    }
  });
  return obj;
}

export type GridDrawMode = 'lines' | 'rects';

export interface WorldConfig {
  // Add more world/business logic config here
}

export interface WorldWindowConfig { 
  readonly canvasWidth: number;
  readonly canvasHeight: number;
  readonly canvasBackgroundColor: string;
  readonly gridColor: string;
  readonly gridLineThickness: number;
  readonly gridLineAlpha: number;
  readonly defaultFontFamily: string;
  readonly cellSize: number;
  readonly gridDrawMode: GridDrawMode;
  // Add more drawing/presentation config here
}

export const worldConfig: Readonly<WorldConfig> = deepFreeze({
  // Add more world/business logic config here
});

export const worldWindowConfig: Readonly<WorldWindowConfig> = deepFreeze({
  canvasWidth: 1200,
  canvasHeight: 800,
  canvasBackgroundColor: '#e45a96',
  gridColor: '#efde74',
  gridLineThickness: 0.5,
  gridLineAlpha: 0.7,
  defaultFontFamily: 'Arial',
  cellSize: 20,
  gridDrawMode: 'lines',
  // Add more drawing/presentation config here
});
