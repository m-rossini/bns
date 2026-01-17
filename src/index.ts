import Phaser from 'phaser';
import { initWorldWindow, worldWindow } from './worldWindow';
import { StatsDashboard } from './dashboards/StatsDashboard';
import { DynamicConfigDashboard } from './dashboards/DynamicConfigDashboard';
import { CommandsDashboard } from './dashboards/CommandsDashboard';
import { drawGrid } from './grid';
import { createAllEventSinks } from './observability/eventSinkFactory';
import { RunContext } from './runContext';
import { UXTracker } from './observability/uxTracker';
import { SimulationTracker } from './observability/simulationTracker';
import { SimulationContext } from './simulationContext';
import { EventType, EventSink } from './observability/types';
import { logWarn, logInfo, logError, logDebug } from './observability/logger';
import { worldConfig, worldWindowConfig, WorldConfig } from './config';
import { uuidv4 } from './utils/uuid';
import { initializeOpenObserveRum } from './observability/rumInitializer';
import { ITimeKeeper } from './world/time/types';

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

/**
 * Dynamically resolves and instantiates a TimeKeeper provider.
 */
async function resolveTimeKeeper(config: WorldConfig['time']): Promise<ITimeKeeper> {
  const { provider, params } = config;
  try {
    logDebug(`Resolving TimeKeeper provider: ${provider}`);
    const module = await import(`./world/time/${provider}.ts`);
    const TimeKeeperClass = module[provider];

    if (!TimeKeeperClass) {
      throw new Error(`Class ${provider} not found in module ./world/time/${provider}.ts`);
    }

    const instance = new TimeKeeperClass(params);
    
    return instance;
  } catch (err) {
    logError(`Failed to load TimeKeeper [${provider}]`, err);
    throw err;
  }
}

function setSimulationCanvasSize() {
  const appDiv = document.getElementById('app');
  if (appDiv) {
    appDiv.style.setProperty('--app-width', `${worldWindowConfig.canvasWidth}px`);
    appDiv.style.setProperty('--app-height', `${worldWindowConfig.canvasHeight}px`);
  }
}

let statsDashboard: StatsDashboard;
let dynamicConfigDashboard: DynamicConfigDashboard;
let commandsDashboard: CommandsDashboard;
let isPaused = false;
let drawGridFn: ((showGrid: boolean) => void) | undefined;

async function bootstrap() {
  const sessionId = uuidv4();
  let runContext: RunContext;

  // Phase 1: Critical Infrastructure (Logging/Trackers ready)
  try {
    const sinks = createAllEventSinks();
    const trackers = RunContext.createTrackers(sinks, sessionId);
    runContext = new RunContext(trackers, sessionId);
    logInfo('RunContext initialized. Telemetry system online.');
  } catch (err) {
    logWarn('Falling back to ConsoleSink due to error creating event sinks:', err);
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

  let timeKeeper: ITimeKeeper;
  try {
    timeKeeper = await resolveTimeKeeper(worldConfig.time);
    runContext.getTracker(SimulationTracker).track('timekeeper_initialized', { provider: worldConfig.time });
  } catch (err) {
    logError('Critical failure: Could not resolve TimeKeeper. Simulation cannot start.', err);
    return;
  }

  // Phase 3: Simulation Assembly
  const simTracker = runContext.getTracker(SimulationTracker);
  const simContext = new SimulationContext(simTracker, timeKeeper, worldConfig, worldWindowConfig);
  initWorldWindow(simContext);

  runContext.getTracker(UXTracker).track('app_startup', { version: '0.1.0' });

  const phaserConfig: Phaser.Types.Core.GameConfig = {
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

        // Instantiate dashboards
        statsDashboard = new StatsDashboard();
        statsDashboard.render(worldWindow.world.state);

        dynamicConfigDashboard = new DynamicConfigDashboard(runContext);
        dynamicConfigDashboard.render();

        const actionsFrame = document.getElementById('actionsFrame');
        if (actionsFrame) {
          commandsDashboard = new CommandsDashboard(
            actionsFrame,
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
        }
      },
      update(time, delta) {
        const speed = dynamicConfigDashboard?.speed ?? 1;
        if (!isPaused) {
          worldWindow.update(time, delta * speed);
        }
        drawGridFn?.(worldWindow.state.showGrid);
        if (statsDashboard) {
          statsDashboard.render(worldWindow.world.state);
        }
      }
    }
  };

  setSimulationCanvasSize();
  new Phaser.Game(phaserConfig);
}

// Start the bootstrap process
bootstrap().catch(err => {
  console.error('CRITICAL BOOTSTRAP FAILURE:', err);
});
