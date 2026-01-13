import Phaser from 'phaser';
import { initWorldWindow, worldWindow } from './worldWindow';
import { StatsDashboard } from './dashboards/StatsDashboard';
import { DynamicConfigDashboard } from './dashboards/DynamicConfigDashboard';
import { CommandsDashboard } from './dashboards/CommandsDashboard';
import { drawGrid } from './grid';
import { createEventSink, createAllEventSinks } from './observability/eventSinkFactory';
import { RunContext } from './runContext';
import { UXTracker } from './observability/uxTracker';
import { SimulationTracker } from './observability/simulationTracker';
import { SimulationContext } from './simulationContext';
import { EventType, EventSink } from './observability/types';
import { logWarn } from './observability/logger';
import { worldConfig, worldWindowConfig } from './config';
import { uuidv4 } from './utils/uuid';
import { initializeOpenObserveRum } from './observability/rumInitializer';

// Initialize OpenObserve RUM if configured
initializeOpenObserveRum();

// Dynamically set container widths based on config
// function setContainerWidths() {
//   const width = worldWindow.config.canvasWidth;
//   const mainContainer = document.getElementById('mainContainer');
//   const appDiv = document.getElementById('app');
//   const optionsFrame = document.getElementById('optionsFrame');
//   if (mainContainer) mainContainer.style.width = width + 'px';
//   if (appDiv) appDiv.style.width = width + 'px';
//   if (optionsFrame) optionsFrame.style.width = width + 'px';
// }

function setSimulationCanvasSize() {
  const appDiv = document.getElementById('app');
  if (appDiv) {
    appDiv.style.setProperty('--app-width', `${worldWindow.config.canvasWidth}px`);
    appDiv.style.setProperty('--app-height', `${worldWindow.config.canvasHeight}px`);
  }
}

let statsDashboard: StatsDashboard;
let dynamicConfigDashboard: DynamicConfigDashboard;
let commandsDashboard: CommandsDashboard;
let isPaused = false;
let drawGridFn: ((showGrid: boolean) => void) | undefined;

// Initialize RunContext. If environment variables are missing, fall back to console sinks.
let runContext: RunContext;
const sessionId = uuidv4();
try {
  const sinks = createAllEventSinks();
  const trackers = RunContext.createTrackers(sinks, sessionId);
  runContext = new RunContext(trackers, sessionId);
} catch (err) {
  logWarn('Falling back to ConsoleSink due to error creating event sinks. Look previous messages for reasons:', err);
  const consoleSink: EventSink = {
    async sendEvent(event): Promise<void> {
      console.info('Event (console sink):', event);
    }
  };
  const sinks = {
    [EventType.UX_ACTION]: consoleSink,
    [EventType.SIMULATION_EVENT]: consoleSink
  };
  const trackers = RunContext.createTrackers(sinks, sessionId);
  runContext = new RunContext(trackers, sessionId);
}

// Initialize Simulation with Dependency Injection
const simTracker = runContext.getTracker(SimulationTracker);
const simContext = new SimulationContext(simTracker, worldConfig, worldWindowConfig);
initWorldWindow(simContext);

runContext.getTracker(UXTracker).track('app_startup', { version: '0.1.0' });

const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  width: worldWindow.config.canvasWidth,
  height: worldWindow.config.canvasHeight,
  backgroundColor: worldWindow.config.canvasBackgroundColor,
  parent: 'app',
  scene: {
    create() {
      const gridGraphics = this.add.graphics();
      drawGridFn = (show: boolean) => drawGrid(gridGraphics, show, worldWindow.config);
      drawGridFn(worldWindow.state.showGrid);

      // Instantiate dashboards in new layout with RunContext
      statsDashboard = new StatsDashboard();
      statsDashboard.render(worldWindow.world.state);

      dynamicConfigDashboard = new DynamicConfigDashboard(runContext);
      dynamicConfigDashboard.render();

      const actionsFrame = document.getElementById('actionsFrame');
      commandsDashboard = new CommandsDashboard(
        actionsFrame!,
        worldWindow.state.showGrid,
        (newShowGrid: boolean) => {
          worldWindow.state.showGrid = newShowGrid;
          drawGridFn?.(worldWindow.state.showGrid);
        },
        (paused: boolean) => {
          isPaused = paused;
        },
        runContext
      );
      commandsDashboard.render();
    },
    update(time: number, delta: number) {
      // Use speed from dynamicConfigDashboard to scale delta
      const speed = dynamicConfigDashboard?.speed ?? 1;
      if (!isPaused) {
        worldWindow.update(time, delta * speed);
      }
      // Always update grid visibility in case it was toggled
      drawGridFn?.(worldWindow.state.showGrid);
      if (statsDashboard) {
        statsDashboard.render(worldWindow.world.state);
      }
    }
  }
};

// Call this function before initializing Phaser
setSimulationCanvasSize();

const game = new Phaser.Game(config);
runContext.game = game;
