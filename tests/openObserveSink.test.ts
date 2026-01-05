// openObserveSink.test.ts
// TDD: OpenObserveSink implementation tests
import { describe, it, expect, vi } from 'vitest';
import { OpenObserveSink } from '../src/openObserveSink';
import { EventType, Event } from '../src/config';

describe('OpenObserveSink', () => {
  it('should log and send event (mocked)', async () => {
    const sink = new OpenObserveSink('http://fake-url', 'fake-key');
    // Mock fetch or HTTP logic here
    const event: Event = {
      id: 'test-id',
      timestamp: new Date().toISOString(),
      eventType: EventType.SIMULATION_EVENT,
      payload: { sim: 1 },
    };
    // This is a placeholder; actual HTTP logic will be tested with mocks
    await expect(sink.sendEvent(event)).resolves.toBeUndefined();
  });
});