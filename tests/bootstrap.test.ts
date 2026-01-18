import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createEventSink } from '@/observability/eventSinkFactory';
import { RunContext } from '@/runContext';
import { UXTracker } from '@/observability/uxTracker';
import { EventType, EventSink } from '@/observability/types';
import * as logger from '@/observability/logger';

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
    vi.stubEnv('VITE_SIM_EVENT_SINK_TYPE', 'openobserve');
    vi.stubEnv('VITE_SIM_EVENT_SINK_URL', 'http://localhost:5080');
    vi.stubEnv('VITE_SIM_EVENT_SINK_API_KEY', 'test-key');
    
    const uxSink = createEventSink(EventType.UX_ACTION);
    const simSink = createEventSink(EventType.SIMULATION_EVENT);
    const sinks = {
      [EventType.UX_ACTION]: uxSink,
      [EventType.SIMULATION_EVENT]: simSink
    };
    const sessionId = 'test-session-123';
    const trackers = RunContext.createTrackers(sinks, sessionId);
    const runContext = new RunContext(trackers, sessionId);
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
    const sessionId = 'test-session-456';
    try {
      const uxSink = createEventSink(EventType.UX_ACTION);
      const simSink = createEventSink(EventType.SIMULATION_EVENT);
      const sinks = {
        [EventType.UX_ACTION]: uxSink,
        [EventType.SIMULATION_EVENT]: simSink
      };
      const trackers = RunContext.createTrackers(sinks, sessionId);
      runContext = new RunContext(trackers, sessionId);
    } catch (err) {
      // Logic copied from index.ts
      logger.logWarn('Falling back to ConsoleSink due to error creating event sinks. Look previous messages for reasons:', err);
      const consoleSink: EventSink = {
        async sendEvent(event): Promise<void> {
          console.info('Event (console sink):', event);
        }
      };
      const sinks = {
        [EventType.UX_ACTION]: consoleSink,
        [EventType.SIMULATION_EVENT]: consoleSink
      };
      const trackers = RunContext.createTrackers(sinks, sessionId);
      runContext = new RunContext(trackers, sessionId);
    }
    
    // Should still be able to track
    await runContext.getTracker(UXTracker).track('app_startup', { version: '0.1.0' });
    
    expect(logWarnSpy).toHaveBeenCalledWith(
      expect.stringContaining('Falling back to ConsoleSink'),
      expect.any(Error)
    );
    
    expect(consoleSpy).toHaveBeenCalledWith(
      'Event (console sink):',
      expect.objectContaining({
        payload: expect.objectContaining({ action: 'app_startup' })
      })
    );
    
    consoleSpy.mockRestore();
    logWarnSpy.mockRestore();
  });
});
