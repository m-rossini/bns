import { EventSink, EventType } from './types';
import { BaseTracker } from './baseTracker';

export class SimulationTracker extends BaseTracker {
  constructor(sink: EventSink, sessionId: string, debounceMs = 300) {
    super(sink, sessionId, EventType.SIMULATION_EVENT, 'event', debounceMs);
  }
}
