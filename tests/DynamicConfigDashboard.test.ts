import { beforeAll, beforeEach, afterEach, describe, it, expect } from 'vitest';
import { DynamicConfigDashboard } from '../src/dashboards/DynamicConfigDashboard';

beforeAll(() => {
  if (typeof window === 'undefined') {
    globalThis.window = {} as any;
    globalThis.document = require('global-jsdom')();
  }
});

describe('DynamicConfigDashboard', () => {
  beforeEach(() => {
    // Create mock configFrame for DynamicConfigDashboard
    const configFrame = document.createElement('div');
    configFrame.id = 'configFrame';
    document.body.appendChild(configFrame);
  });

  afterEach(() => {
    // Clean up mock configFrame
    const configFrame = document.getElementById('configFrame');
    if (configFrame) configFrame.remove();
  });

  it('should instantiate without error', () => {
    const dashboard = new DynamicConfigDashboard();
    expect(dashboard).toBeInstanceOf(DynamicConfigDashboard);
  });

  it('collapses correctly', () => {
    const dashboard = new DynamicConfigDashboard();
    dashboard.collapse();
    // Access the private contentWrapper via a workaround for test
    const contentWrapper = (dashboard as any).contentWrapper as HTMLDivElement;
    expect(contentWrapper.style.display).toBe('none');
    // Optionally check collapseButton text
    expect((dashboard as any).collapseButton.textContent).toBe('▶');
  });

  it('expands correctly', () => {
    const dashboard = new DynamicConfigDashboard();
    dashboard.collapse();
    dashboard.expand();
    const contentWrapper = (dashboard as any).contentWrapper as HTMLDivElement;
    expect(contentWrapper.style.display).toBe('block');
    expect((dashboard as any).collapseButton.textContent).toBe('◀');
  });
});
