import { EventSink, EventType } from '@/observability/types';
import { BaseTracker } from '@/observability/baseTracker';

export class UXTracker extends BaseTracker {
  constructor(sink: EventSink, sessionId: string, debounceMs = 300) {
    super(sink, sessionId, EventType.UX_ACTION, 'action', debounceMs);
  }
}
