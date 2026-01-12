import { EventSink } from "./eventSink";
import { OpenObserveSink } from "./openObserveSink";
import { logInfo, logError } from "./logger";
import { EventType } from "./types";
import { logDebug } from '../observability/logger';

function requireEnv(key: string): string {
  // @ts-ignore
  const value = import.meta.env[key];
  if (!value) {
    logError(`Missing required environment variable: ${key}`);
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

export function createEventSink(eventType: EventType): EventSink {
  let sinkType: string, url: string, apiKey: string;
  logDebug(`>>>createEventSink: eventType=${eventType}`);

  switch (eventType) {
    case EventType.UX_ACTION:
      sinkType = requireEnv('VITE_UX_EVENT_SINK_TYPE');
      url = requireEnv('VITE_UX_EVENT_SINK_URL');
      apiKey = requireEnv('VITE_UX_EVENT_SINK_API_KEY');
      break;
    case EventType.SIMULATION_EVENT:
      sinkType = requireEnv('VITE_SIM_EVENT_SINK_TYPE');
      url = requireEnv('VITE_SIM_EVENT_SINK_URL');
      apiKey = requireEnv('VITE_SIM_EVENT_SINK_API_KEY');
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
