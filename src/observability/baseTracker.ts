import { uuidv4 } from '../utils/uuid';
import { Event, EventSink, EventType, Tracker } from './types';
import { logDebug } from './logger';

export type PendingEvent = {
  timeoutId: ReturnType<typeof setTimeout> | null;
  lastPayload: Record<string, unknown>;
};

export abstract class BaseTracker implements Tracker {
  protected pending: Map<string, PendingEvent> = new Map();

  constructor(
    protected sink: EventSink,
    protected sessionId: string,
    protected eventType: EventType,
    protected labelKey: string,
    protected debounceMs: number = 300
  ) {}

  public track(label: string, payload: Record<string, unknown> = {}, debounce: boolean = false): void {
    logDebug(`>>> ${this.constructor.name}.track: ${this.labelKey}=${label}, debounce=${debounce}`, payload);
    
    if (!debounce) {
      const ev: Event = this.createEvent(label, payload);
      void this.sink.sendEvent(ev);
      return;
    }

    const existing = this.pending.get(label);
    if (existing && existing.timeoutId) {
      existing.lastPayload = { ...existing.lastPayload, ...payload };
      clearTimeout(existing.timeoutId);
      existing.timeoutId = setTimeout(() => this.flush(label), this.debounceMs);
      return;
    }

    const timeoutId = setTimeout(() => this.flush(label), this.debounceMs);
    this.pending.set(label, { timeoutId, lastPayload: payload });
  }

  protected createEvent(label: string, payload: Record<string, unknown>): Event {
    return {
      id: uuidv4(),
      timestamp: new Date().toISOString(),
      eventType: this.eventType,
      sessionId: this.sessionId,
      payload: { [this.labelKey]: label, ...payload },
    };
  }

  protected flush(label: string): void {
    const p = this.pending.get(label);
    if (!p) return;
    
    const ev = this.createEvent(label, p.lastPayload);
    void this.sink.sendEvent(ev);
    
    if (p.timeoutId) clearTimeout(p.timeoutId);
    this.pending.delete(label);
  }
}
