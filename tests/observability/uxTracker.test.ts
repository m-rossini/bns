import { describe, it, expect } from 'vitest';
import { UXTracker } from '../../src/observability/uxTracker';
import { Event } from '../../src/observability/types';

class FakeSink {
  public events: Event[] = [];
  async sendEvent(event: Event): Promise<void> {
    this.events.push(event);
  }
}

function delay(ms: number) {
  return new Promise((res) => setTimeout(res, ms));
}

describe('UXTracker', () => {
  it('sends immediate events without debounce', async () => {
    const sink = new FakeSink();
    const tracker = new UXTracker(sink as any, 'session-1', 50);
    tracker.track('toggle_grid', { visible: true }, false);
    // give microtask a chance
    await delay(10);
    expect(sink.events.length).toBe(1);
    const ev = sink.events[0];
    expect(ev.eventType).toBeDefined();
    expect(ev.payload).toHaveProperty('action', 'toggle_grid');
    expect(ev.sessionId).toBe('session-1');
  });

  it('debounces high-frequency events and emits only last payload', async () => {
    const sink = new FakeSink();
    const debounceMs = 60;
    const tracker = new UXTracker(sink as any, 'session-2', debounceMs);
    tracker.track('speed_change', { speed: 1 }, true);
    tracker.track('speed_change', { speed: 2 }, true);
    tracker.track('speed_change', { speed: 3 }, true);
    // wait longer than debounce
    await delay(debounceMs + 40);
    expect(sink.events.length).toBe(1);
    const ev = sink.events[0];
    expect(ev.payload).toHaveProperty('speed', 3);
    expect(ev.sessionId).toBe('session-2');
  });
});
