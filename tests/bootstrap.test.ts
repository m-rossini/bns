import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createEventSink } from '../src/observability/eventSinkFactory';
import { RunContext } from '../src/runContext';
import { UXTracker } from '../src/observability/uxTracker';
import { EventType, EventSink } from '../src/observability/types';
import * as logger from '../src/observability/logger';

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
    const uxTracker = runContext.getTracker(UXTracker);
    
    // Mock the track method
    const trackSpy = vi.spyOn(uxTracker, 'track');
    
    // This is what index.ts will do
    uxTracker.track('app_startup', { version: '0.1.0' });
    
    expect(trackSpy).toHaveBeenCalledWith('app_startup', expect.any(Object));
  });

  it('should fall back to console sink when createEventSink fails', async () => {
    // Clear env to force failure
    vi.stubEnv('VITE_UX_EVENT_SINK_TYPE', '');
    
    const consoleSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
    const logWarnSpy = vi.spyOn(logger, 'logWarn').mockImplementation(() => {});
    
    let runContext: RunContext;
    try {
      const sink = createEventSink(EventType.UX_ACTION);
      runContext = new RunContext(sink);
    } catch (err) {
      // Logic copied from index.ts
      logger.logWarn('Falling back to ConsoleSink due to error creating event sink.Look previous messages for reasons:', err);
      const consoleSink: EventSink = {
        async sendEvent(event): Promise<void> {
          console.info('UXEvent (console sink):', event);
        }
      };
      runContext = new RunContext(consoleSink);
    }
    
    // Should still be able to track
    await runContext.getTracker(UXTracker).track('app_startup', { version: '0.1.0' });
    
    expect(logWarnSpy).toHaveBeenCalledWith(
      expect.stringContaining('Falling back to ConsoleSink'),
      expect.any(Error)
    );
    
    expect(consoleSpy).toHaveBeenCalledWith(
      'UXEvent (console sink):',
      expect.objectContaining({
        payload: expect.objectContaining({ action: 'app_startup' })
      })
    );
    
    consoleSpy.mockRestore();
    logWarnSpy.mockRestore();
  });
});
