export enum EventType {
  UX_ACTION = 'ux_action',
  SIMULATION_EVENT = 'simulation_event'
}

export interface Event {
  id: string;
  timestamp: string; // ISO
  eventType: EventType;
  userId?: string;
  sessionId?: string;
  payload: Record<string, unknown>;
}

export interface EventSink {
  sendEvent(event: Event): Promise<void>;
}
