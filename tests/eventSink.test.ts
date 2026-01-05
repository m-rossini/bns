// eventSink.test.ts
// TDD: EventSink abstraction tests
import { describe, it, expect } from 'vitest';
import { EventType, Event } from '../src/config';
import { EventSink } from '../src/eventSink';

// Example mock sink for testing
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