import { logDebug } from './logger';
import { EventType, Event, EventSink } from './types';
import { uuidv4 } from '../utils/uuid';

type Pending = {
  timeoutId: ReturnType<typeof setTimeout> | null;
  lastPayload: Record<string, unknown>;
};

export class UXTracker {
  private pending: Map<string, Pending> = new Map();

  constructor(private sink: EventSink, private sessionId: string, private debounceMs = 300) {}

  track(action: string, payload: Record<string, unknown> = {}, debounce = false) {
    logDebug(`>>>UXTracker.track: action=${action}, debounce=${debounce}`, payload);
    if (!debounce) {
      const ev: Event = {
        id: uuidv4(),
        timestamp: new Date().toISOString(),
        eventType: EventType.UX_ACTION,
        sessionId: this.sessionId,
        payload: { action, ...payload },
      };
      // fire-and-forget
      void this.sink.sendEvent(ev);
      return;
    }

    const existing = this.pending.get(action);
    if (existing && existing.timeoutId) {
      // update payload and reset timer
      existing.lastPayload = { ...existing.lastPayload, ...payload };
      clearTimeout(existing.timeoutId);
      existing.timeoutId = setTimeout(() => this.flush(action), this.debounceMs);
      return;
    }

    const timeoutId = setTimeout(() => this.flush(action), this.debounceMs);
    this.pending.set(action, { timeoutId, lastPayload: payload });
  }

  private flush(action: string) {
    const p = this.pending.get(action);
    if (!p) return;
    const ev: Event = {
      id: uuidv4(),
      timestamp: new Date().toISOString(),
      eventType: EventType.UX_ACTION,
      sessionId: this.sessionId,
      payload: { action, ...p.lastPayload },
    };
    void this.sink.sendEvent(ev);
    if (p.timeoutId) clearTimeout(p.timeoutId);
    this.pending.delete(action);
  }
}
