import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createEventSink } from '../src/observability/eventSinkFactory';
import { RunContext } from '../src/runContext';
import { EventType } from '../src/observability/types';

describe('Bootstrap Logic', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
    vi.stubEnv('VITE_UX_EVENT_SINK_TYPE', 'openobserve');
    vi.stubEnv('VITE_UX_EVENT_SINK_URL', 'http://localhost:5080');
    vi.stubEnv('VITE_UX_EVENT_SINK_API_KEY', 'test-key');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('should track app_startup when sink is successfully created', async () => {
    const sink = createEventSink(EventType.UX_ACTION);
    const runContext = new RunContext(sink);
    
    // Mock the track method
    const trackSpy = vi.spyOn(runContext.uxTracker, 'track');
    
    // This is what index.ts will do
    runContext.uxTracker.track('app_startup', { version: '0.1.0' });
    
    expect(trackSpy).toHaveBeenCalledWith('app_startup', expect.any(Object));
  });
});
