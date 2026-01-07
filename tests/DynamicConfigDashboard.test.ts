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
    const container = document.createElement('div');
    const dashboard = new DynamicConfigDashboard(container);
    expect(dashboard).toBeInstanceOf(DynamicConfigDashboard);
  });
});
