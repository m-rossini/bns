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
  defaultFontFamily?: string;
  // Future: Add more graphical properties here
}


export const graphicsConfig: SimulationGraphicsConfig = {
  canvasWidth: 800,
  canvasHeight: 800,
  canvasBackgroundColor: '#d7ffec',
  showGrid: true, // Default: grid is shown
  gridColor: '#393a3aff',
  gridStep: 20, // Default grid step
  gridLineThickness: 1,
  gridLineAlpha: 0.7,
  defaultFontFamily: 'Arial',
};

// Future: Add world, beans, and environment config sections
