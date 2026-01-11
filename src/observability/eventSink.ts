import { Event } from "./types";

export interface EventSink {
  sendEvent(event: Event): Promise<void>;
}
