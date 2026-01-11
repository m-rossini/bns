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
  console.log(`>>>createEventSink: eventType=${eventType}`);
  // Detect browser environment
  const isBrowser = typeof window !== 'undefined' && typeof window.document !== 'undefined';
  // Detect test environment (Vitest/Jest) to avoid treating test runner as a real browser
  const isTestEnv = typeof process !== 'undefined' && ((process as any).env && ((process as any).env.NODE_ENV === 'test' || (process as any).env.VITEST));

  // Helper: read env safely (works in Node). In browser we won't rely on process.env.
  function getEnvNode(key: string): string | undefined {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if (typeof process === 'undefined' || !(process as any).env) return undefined;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (process as any).env[key];
  }

  // Console sink fallback for browsers/local dev
  class ConsoleSink implements EventSink {
    async sendEvent(event: any): Promise<void> {
      // use logInfo/logError from logger for consistent formatting
      logInfo(`ConsoleSink event: ${event?.eventType ?? 'unknown'}`);
      // eslint-disable-next-line no-console
      console.log('Event:', event);
    }
  }

  // Prefer process.env values (works in Node and test env). If missing and running
  // in a real browser, fall back to ConsoleSink; otherwise (Node) enforce required env.
  switch (eventType) {
    case EventType.UX_ACTION:
      sinkType = getEnvNode('UX_EVENT_SINK_TYPE') ?? '';
      url = getEnvNode('UX_EVENT_SINK_URL') ?? '';
      apiKey = getEnvNode('UX_EVENT_SINK_API_KEY') ?? '';
      break;
    case EventType.SIMULATION_EVENT:
      sinkType = getEnvNode('SIM_EVENT_SINK_TYPE') ?? '';
      url = getEnvNode('SIM_EVENT_SINK_URL') ?? '';
      apiKey = getEnvNode('SIM_EVENT_SINK_API_KEY') ?? '';
      break;
    default:
      logError(`Unknown event type: ${eventType}`);
      throw new Error(`Unknown event type: ${eventType}`);
  }
  console.log(`>>>createEventSink: sinkType=${sinkType}, url=${url ? 'provided' : 'missing'}, apiKey=${apiKey ? 'provided' : 'missing'}`);
  if (!sinkType || !url || !apiKey) {
    if (isBrowser && !isTestEnv) {
      logInfo('Event sink config incomplete or running in browser; returning ConsoleSink fallback');
      return new ConsoleSink();
    }
    // Node (or test) - enforce environment variables for strictness
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
  }


  if (!sinkType || !url || !apiKey) {
    logInfo('Event sink config incomplete or running in browser; returning ConsoleSink fallback');
    return new ConsoleSink();
  }

  logInfo(`Creating event sink for ${eventType}: ${sinkType}`);
  switch (sinkType) {
    case 'openobserve':
      return new OpenObserveSink(url, apiKey);
    // Add more sink types here as needed
    default:
      logError(`Unknown sink type: ${sinkType}`);
      throw new Error(`Unknown sink type: ${sinkType}`);
  }
}
