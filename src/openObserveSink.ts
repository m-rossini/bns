import { EventSink } from "./eventSink";
import { Event } from "./config";
import { logInfo, logError } from "./logger";

export class OpenObserveSink implements EventSink {
  constructor(private url: string, private apiKey: string) {}

  async sendEvent(event: Event): Promise<void> {
    try {
      // POST event to OpenObserve
      logInfo(`Sending event to OpenObserve: ${event.eventType}`);
      // ...HTTP POST logic...
      logInfo("Event sent successfully");
    } catch (err) {
      logError("Failed to send event", err);
      // Optionally retry or escalate
    }
  }
}
