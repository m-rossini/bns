import { describe, it, expect } from 'vitest';
import { EventType, Event, EventSink } from '../../src/observability/types';

describe('EventSink', () => {
  it('should implement sendEvent(event)', async () => {
    class MockSink implements EventSink {
      async sendEvent(event: Event) {
        return Promise.resolve();
      }
    }
    const sink = new MockSink();
    const event: Event = {
      id: 'test-id',
      timestamp: new Date().toISOString(),
      eventType: EventType.UX_ACTION,
      payload: { foo: 'bar' },
    };
    await expect(sink.sendEvent(event)).resolves.toBeUndefined();
  });
});