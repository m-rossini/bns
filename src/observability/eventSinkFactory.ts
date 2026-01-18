import { OpenObserveSink } from "@/observability/openObserveSink";
import { logInfo, logError, logDebug } from "@/observability/logger";
import { EventType, EventSink } from "@/observability/types";

export type EventSinkMap = {
  [EventType.UX_ACTION]?: EventSink;
  [EventType.SIMULATION_EVENT]?: EventSink;
};

function requireEnv(key: string): string {
  const env = import.meta.env as Record<string, string | undefined>;
  const value = env[key];
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
/**
 * Creates all required event sinks for the application.
 * Each event type gets its own sink configured via environment variables.
 */
export function createAllEventSinks(): EventSinkMap {
  const sinks: EventSinkMap = {};
  
  try {
    sinks[EventType.UX_ACTION] = createEventSink(EventType.UX_ACTION);
  } catch (err) {
    logError('Failed to create UX_ACTION sink', err);
    throw err;
  }

  try {
    sinks[EventType.SIMULATION_EVENT] = createEventSink(EventType.SIMULATION_EVENT);
  } catch (err) {
    logError('Failed to create SIMULATION_EVENT sink', err);
    throw err;
  }

  return sinks;
}