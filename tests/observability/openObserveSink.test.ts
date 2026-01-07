// Moved from tests/openObserveSink.test.ts
// Updated imports to reflect new file paths
import { describe, it, expect, vi } from 'vitest';
import { OpenObserveSink } from '../../src/observability/openObserveSink';
import { EventType, Event } from '../../src/config';

describe('OpenObserveSink', () => {
  it('should log and send event (mocked)', async () => {
    const sink = new OpenObserveSink('http://fake-url', 'fake-key');
    const event: Event = {
      id: 'test-id',
      timestamp: new Date().toISOString(),
      eventType: EventType.SIMULATION_EVENT,
      payload: { sim: 1 },
    };
    await expect(sink.sendEvent(event)).resolves.toBeUndefined();
  });
});