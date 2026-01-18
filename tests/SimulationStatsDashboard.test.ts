import { beforeAll } from 'vitest';

beforeAll(() => {
  if (typeof window === 'undefined') {
    globalThis.window = {} as any;
    globalThis.document = require('global-jsdom')();
  }
});
import { describe, it, expect } from 'vitest';
import { SimulationStatsDashboard } from '@/dashboards/SimulationStatsDashboard';

describe('SimulationStatsDashboard', () => {
  it('should instantiate without error', () => {
    const container = document.createElement('div');
    const dashboard = new SimulationStatsDashboard(container);
    expect(dashboard).toBeInstanceOf(SimulationStatsDashboard);
  });
});
