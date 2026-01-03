// Simulation graphical configuration
// Extend this interface to add world, beans, and environment settings


export interface SimulationGraphicsConfig {
  canvasWidth: number;
  canvasHeight: number;
  backgroundColor: string;
  showGrid: boolean; // Toggle grid display
  gridColor: string;
  // Future: Add more graphical properties here
}


export const graphicsConfig: SimulationGraphicsConfig = {
  canvasWidth: 1400,
  canvasHeight: 800,
  backgroundColor: '#c81e1e',
  showGrid: true, // Default: grid is shown
  gridColor: '#5cad15',
};

// Future: Add world, beans, and environment config sections
