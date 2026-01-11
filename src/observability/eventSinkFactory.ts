import { EventSink } from "./eventSink";
import { OpenObserveSink } from "./openObserveSink";
import { logInfo, logError } from "./logger";
import { EventType } from "./types";

function requireEnv(key: string): string {
  const value = process.env[key];
  if (!value) {
    logError(`Missing required environment variable: ${key}`);
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

export function createEventSink(eventType: EventType): EventSink {
  let sinkType: string, url: string, apiKey: string;
  console.log(0, `>>>createEventSink: eventType=${eventType}`);

  switch (eventType) {
    case EventType.UX_ACTION:
      sinkType = requireEnv('UX_EVENT_SINK_TYPE');
      url = requireEnv('UX_EVENT_SINK_URL');
      apiKey = requireEnv('UX_EVENT_SINK_API_KEY');
      break;
    case EventType.SIMULATION_EVENT:
      sinkType = requireEnv('SIM_EVENT_SINK_TYPE');
      url = requireEnv('SIM_EVENT_SINK_URL');
      apiKey = requireEnv('SIM_EVENT_SINK_API_KEY');
      break;
    default:
      logError(`Unknown event type: ${eventType}`);
      throw new Error(`Unknown event type: ${eventType}`);
  }


  logInfo(`Creating event sink for ${eventType}: ${sinkType}`);
  switch (sinkType) {
    case 'openobserve':
      return new OpenObserveSink(url, apiKey);
    default:
      logError(`Unknown sink type: ${sinkType}`);
      throw new Error(`Unknown sink type: ${sinkType}`);
  }
}
