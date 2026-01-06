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
