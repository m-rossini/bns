import { beforeAll } from 'vitest';

beforeAll(() => {
  if (typeof window === 'undefined') {
    globalThis.window = {} as any;
    globalThis.document = require('global-jsdom')();
  }
});
import { describe, it, expect } from 'vitest';
import { DynamicConfigDashboard } from '../src/dashboards/DynamicConfigDashboard';

describe('DynamicConfigDashboard', () => {
  it('should instantiate without error', () => {
    const dashboard = new DynamicConfigDashboard();
    expect(dashboard).toBeInstanceOf(DynamicConfigDashboard);
  });

  it('collapses correctly', () => {
    const dashboard = new DynamicConfigDashboard();
    dashboard.collapse();
    // Access the private configDiv via a workaround for test
    const configDiv = (dashboard as any).configDiv as HTMLDivElement;
    expect(configDiv.style.height).toBe('20px');
    expect(configDiv.innerHTML).toContain('+');
  });

  it('expands correctly', () => {
    const dashboard = new DynamicConfigDashboard();
    dashboard.collapse();
    dashboard.expand();
    const configDiv = (dashboard as any).configDiv as HTMLDivElement;
    expect(configDiv.style.height).toBe('');
    expect(configDiv.innerHTML).not.toContain('+');
  });
});
