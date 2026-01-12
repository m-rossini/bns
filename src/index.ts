import Phaser from 'phaser';
import { worldWindow } from './worldWindow';
import { StatsDashboard } from './dashboards/StatsDashboard';
import { DynamicConfigDashboard } from './dashboards/DynamicConfigDashboard';
import { CommandsDashboard } from './dashboards/CommandsDashboard';
import { drawGrid } from './grid';
import { createEventSink } from './observability/eventSinkFactory';
import { RunContext } from './runContext';
import { EventType } from './observability/types';
import { EventSink } from './observability/eventSink';
import { logWarn } from './observability/logger';



// Dynamically set container widths based on config
function setContainerWidths() {
  const width = worldWindow.config.canvasWidth;
  const mainContainer = document.getElementById('mainContainer');
  const appDiv = document.getElementById('app');
  const optionsFrame = document.getElementById('optionsFrame');
  if (mainContainer) mainContainer.style.width = width + 'px';
  if (appDiv) appDiv.style.width = width + 'px';
  if (optionsFrame) optionsFrame.style.width = width + 'px';
}

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

// Initialize RunContext. If environment variables are missing, fall back to a console sink.
let runContext: RunContext;
try {
  const sink = createEventSink(EventType.UX_ACTION);
  runContext = new RunContext(sink);
} catch (err) {
  logWarn('Falling back to ConsoleSink due to error creating event sink.Look previous messages for reasons:', err);
  const consoleSink: EventSink = {
    async sendEvent(event): Promise<void> {
      console.info('UXEvent (console sink):', event);
    }
  };
  runContext = new RunContext(consoleSink);
}

runContext.uxTracker.track('app_startup', { version: '0.1.0' });

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
      statsDashboard.render();

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
        statsDashboard.render();
      }
    }
  }
};

// Call this function before initializing Phaser
setSimulationCanvasSize();

const game = new Phaser.Game(config);
runContext.game = game;
