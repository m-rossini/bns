import { beforeAll } from 'vitest';

beforeAll(() => {
  if (typeof window === 'undefined') {
    globalThis.window = {} as any;
    globalThis.document = require('global-jsdom')();
  }
});
import { describe, it, expect } from 'vitest';
import { StatsDashboard } from '../src/dashboards/StatsDashboard';

describe('StatsDashboard', () => {
  it('should instantiate without error', () => {
    const container = document.createElement('div');
    const dashboard = new StatsDashboard(container);
    expect(dashboard).toBeInstanceOf(StatsDashboard);
  });
});
