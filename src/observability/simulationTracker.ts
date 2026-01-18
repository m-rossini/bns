import { EventSink, EventType } from '@/observability/types';
import { BaseTracker } from '@/observability/baseTracker';

export class SimulationTracker extends BaseTracker {
  constructor(sink: EventSink, sessionId: string, debounceMs = 300) {
    super(sink, sessionId, EventType.SIMULATION_EVENT, 'event', debounceMs);
  }
}
