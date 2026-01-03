// Simulation graphical configuration
// Extend this interface to add world, beans, and environment settings


export interface SimulationGraphicsConfig {
  canvasWidth: number;
  canvasHeight: number;
  canvasBackgroundColor: string;
  showGrid: boolean; // Toggle grid display
  gridColor: string;
  gridStep?: number; // Grid step size (optional, calculated if not set)
  gridLineThickness?: number; // Grid line thickness
  gridLineAlpha?: number; // Grid line alpha
  titleFontSize?: number;
  defaultFontFamily?: string;
  titleFontColor?: string;
  titlePosition?: { x: number; y: number };
  optionsFrameBackgroundColor?: string;
  // Future: Add more graphical properties here
}


export const graphicsConfig: SimulationGraphicsConfig = {
  canvasWidth: 800,
  canvasHeight: 800,
  canvasBackgroundColor: '#c81e1e',
  showGrid: true, // Default: grid is shown
  gridColor: '#5cad15',
  gridStep: 40, // Default grid step
  gridLineThickness: 1,
  gridLineAlpha: 0.7,
  titleFontSize: 32,
  defaultFontFamily: 'Arial',
  titleFontColor: '#fff',
  titlePosition: undefined, // If undefined, will be centered
  optionsFrameBackgroundColor: '#222',
};

// Future: Add world, beans, and environment config sections
