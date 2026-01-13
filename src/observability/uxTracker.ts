import { EventSink, EventType } from './types';
import { BaseTracker } from './baseTracker';

export class UXTracker extends BaseTracker {
  constructor(sink: EventSink, sessionId: string, debounceMs = 300) {
    super(sink, sessionId, EventType.UX_ACTION, 'action', debounceMs);
  }
}
