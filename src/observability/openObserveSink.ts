import { Event, EventSink } from "./types";
import { logInfo, logError, logDebug } from "./logger";

export class OpenObserveSink implements EventSink {
  constructor(private url: string, private apiKey: string) {}

  async sendEvent(event: Event): Promise<void> {
    logDebug(`OpenObserveSink.sendEvent: eventType=${event.eventType}`, event);
    try {
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
    } catch (err) {
      logError("Failed to send event", err);
    }
  }
}
