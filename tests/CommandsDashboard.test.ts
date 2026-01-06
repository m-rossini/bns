import { SimulationStatsDashboard } from '../src/SimulationStatsDashboard';
import { StatsDashboard } from '../src/StatsDashboard';
import { DynamicConfigDashboard } from '../src/DynamicConfigDashboard';

describe('Dashboard integration', () => {
  it('should instantiate and render all dashboards without error', () => {
    const mainContainer = document.createElement('div');
    const optionsFrame = document.createElement('div');
    const simStatsDashboard = new SimulationStatsDashboard(mainContainer);
    simStatsDashboard.render();
    const statsDashboard = new StatsDashboard(mainContainer);
    statsDashboard.render();
    const dynamicConfigDashboard = new DynamicConfigDashboard(mainContainer);
    dynamicConfigDashboard.render();
    const commandsDashboard = new CommandsDashboard(optionsFrame, false, () => {});
    commandsDashboard.render();
    expect(mainContainer.querySelectorAll('div').length).toBeGreaterThanOrEqual(0);
    expect(optionsFrame.querySelector('button')).not.toBeNull();
  });
});
import { beforeAll } from 'vitest';

beforeAll(() => {
  if (typeof window === 'undefined') {
    globalThis.window = {} as any;
    globalThis.document = require('global-jsdom')();
  }
});
import { describe, it, expect } from 'vitest';
import { CommandsDashboard } from '../src/CommandsDashboard';

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
    const button = container.querySelector('button');
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
    const button = container.querySelector('button')!;
    button.click();
    expect(button.textContent).toBe('Hide Grid');
    expect(callbackCalled).toBe(true);
    expect(callbackValue).toBe(true);
  });
});
