import { EventSink } from "./eventSink";
import { Event } from "./types";
import { logInfo, logError } from "./logger";

export class OpenObserveSink implements EventSink {
  constructor(private url: string, private apiKey: string) {}

  async sendEvent(event: Event): Promise<void> {
    console.debug(`>>>OpenObserveSink.sendEvent: eventType=${event.eventType}`, event);
    try {
      logInfo(`Sending event to OpenObserve: ${event.eventType}`);
      
      const response = await fetch(this.url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': this.apiKey,
        },
        body: JSON.stringify(event),
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'No error detail');
        throw new Error(`OpenObserve ingestion failed (${response.status}): ${errorText}`);
      }

      logInfo("Event sent successfully");
    } catch (err) {
      logError("Failed to send event", err);
    }
  }
}
