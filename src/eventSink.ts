import { Event } from "./config";

export interface EventSink {
  sendEvent(event: Event): Promise<void>;
}
