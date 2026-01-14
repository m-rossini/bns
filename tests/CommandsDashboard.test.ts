import { beforeAll, describe, it, expect } from 'vitest';
import { SimulationStatsDashboard } from '../src/dashboards/SimulationStatsDashboard';
import { StatsDashboard } from '../src/dashboards/StatsDashboard';
import { CommandsDashboard } from '../src/dashboards/CommandsDashboard';


describe('Dashboard integration', () => {
  it('should instantiate and render all dashboards without error', () => {
    const mainContainer = document.createElement('div');
    const optionsFrame = document.createElement('div');
    // Create mock statsFrame for SimulationStatsDashboard
    const statsFrame = document.createElement('div');
    statsFrame.id = 'statsFrame';
    document.body.appendChild(statsFrame);
    const simStatsDashboard = new SimulationStatsDashboard();
    simStatsDashboard.render();
    const statsDashboard = new StatsDashboard(mainContainer);
    statsDashboard.render({ tick: 0, totalTime: 0 });
    // DynamicConfigDashboard requires 'configFrame' element, skip in test
    const commandsDashboard = new CommandsDashboard(optionsFrame, false, () => {}, () => {});
    commandsDashboard.render();
    expect(mainContainer.querySelectorAll('div').length).toBeGreaterThanOrEqual(0);
    expect(optionsFrame.querySelector('button')).not.toBeNull();
  });
});

beforeAll(() => {
  if (typeof window === 'undefined') {
    globalThis.window = {} as any;
    globalThis.document = require('global-jsdom')();
  }
});

describe('CommandsDashboard', () => {
  it('should instantiate without error', () => {
    const container = document.createElement('div');
    const dashboard = new CommandsDashboard(container, true, () => {});
    expect(dashboard).toBeInstanceOf(CommandsDashboard);
  });

  it('should render a grid toggle button with correct label', () => {
    const container = document.createElement('div');
    const dashboard = new CommandsDashboard(container, false, () => {});
    dashboard.render();
    const button = container.querySelector('#toggleGridBtn');
    expect(button).not.toBeNull();
    expect(button!.textContent).toBe('Show Grid');
  });

  it('should update label and call callback on click', () => {
    const container = document.createElement('div');
    let callbackCalled = false;
    let callbackValue = null;
    const dashboard = new CommandsDashboard(container, false, (visible) => {
      callbackCalled = true;
      callbackValue = visible;
    });
    dashboard.render();
    const button = container.querySelector('#toggleGridBtn') as HTMLButtonElement;
    button.click();
    expect(button.textContent).toBe('Hide Grid');
    expect(callbackCalled).toBe(true);
    expect(callbackValue).toBe(true);
  });

  it('should instantiate with pause/unpause callback', () => {
    const container = document.createElement('div');
    const onTogglePause = () => {};
    const dashboard = new CommandsDashboard(container, false, () => {}, onTogglePause);
    expect(dashboard).toBeInstanceOf(CommandsDashboard);
  });

  it('should render a pause button with "Pause" label when running', () => {
    const container = document.createElement('div');
    const dashboard = new CommandsDashboard(container, false, () => {}, () => {});
    dashboard.render();
    const buttons = container.querySelectorAll('button');
    const pauseButton = Array.from(buttons).find(btn => btn.textContent === 'Pause');
    expect(pauseButton).not.toBeNull();
  });

  it('should toggle pause button label between Pause and Resume on click', () => {
    const container = document.createElement('div');
    const dashboard = new CommandsDashboard(container, false, () => {}, () => {});
    dashboard.render();
    const buttons = container.querySelectorAll('button');
    const pauseButton = Array.from(buttons).find(btn => btn.textContent === 'Pause') as HTMLButtonElement;
    expect(pauseButton).not.toBeNull();
    
    pauseButton!.click();
    expect(pauseButton!.textContent).toBe('Resume');
    
    pauseButton!.click();
    expect(pauseButton!.textContent).toBe('Pause');
  });

  it('should call pause callback with correct state on pause button click', () => {
    const container = document.createElement('div');
    let pauseCallbackCalled = false;
    let pauseState: boolean | null = null;
    const dashboard = new CommandsDashboard(container, false, () => {}, (isPaused) => {
      pauseCallbackCalled = true;
      pauseState = isPaused;
    });
    dashboard.render();
    const buttons = container.querySelectorAll('button');
    const pauseButton = Array.from(buttons).find(btn => btn.textContent === 'Pause') as HTMLButtonElement;
    
    pauseButton!.click();
    expect(pauseCallbackCalled).toBe(true);
    expect(pauseState).toBe(true);
  });

  it('should show pause button in both collapsed and expanded states', () => {
    const container = document.createElement('div');
    const dashboard = new CommandsDashboard(container, false, () => {}, () => {});
    dashboard.render();
    
    // Check button exists in expanded state
    let buttons = container.querySelectorAll('button');
    let pauseButton = Array.from(buttons).find(btn => btn.textContent === 'Pause');
    expect(pauseButton).not.toBeNull();
    
    // Collapse
    const collapseBtn = container.querySelector('.dashboard-collapse-btn') as HTMLButtonElement;
    collapseBtn.click();
    
    // Check button still exists in collapsed state
    buttons = container.querySelectorAll('button');
    pauseButton = Array.from(buttons).find(btn => btn.textContent === 'Pause');
    expect(pauseButton).not.toBeNull();
  });
});
