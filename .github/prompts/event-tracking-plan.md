## Plan: Detailed Event Tracking System (Interfaces & Designs)

A comprehensive, step-by-step plan including all interfaces, enums, factory, and logging design for a real-time, extensible event tracking system.

---

### 1. TDD-Style Tests
- Create `eventSink.test.ts`, `openObserveSink.test.ts`, `eventSinkFactory.test.ts`, and `logger.test.ts`.
- Test event validation, sink selection, OpenObserve delivery, and logging for both UX and simulation events.

---

### 2. `.env` Environmental Configs
- Add to project root and `.gitignore`.
- Keys:
  - `UX_EVENT_SINK_TYPE` (e.g., `openobserve`, `mock`)
  - `UX_EVENT_SINK_URL`
  - `UX_EVENT_SINK_API_KEY`
  - `SIM_EVENT_SINK_TYPE`
  - `SIM_EVENT_SINK_URL`
  - `SIM_EVENT_SINK_API_KEY`
- Use `dotenv` for loading.

---

### 3. Event Type Enum & Event Interface

**In `src/config.ts`:**
```ts
export enum EventType {
  UX_ACTION = "ux_action",
  SIMULATION_EVENT = "simulation_event"
}

export interface Event {
  id: string; // UUID
  timestamp: string; // ISO string
  eventType: EventType;
  userId?: string;
  sessionId?: string;
  payload: Record<string, unknown>;
}
```

---

### 4. EventSink Interface

**In `src/eventSink.ts`:**
```ts
import { Event } from "./config";
export interface EventSink {
  sendEvent(event: Event): Promise<void>;
}
```

---

### 5. OpenObserveSink Implementation

**In `src/openObserveSink.ts`:**
```ts
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
```

---

### 6. EventSink Factory

**In `src/eventSinkFactory.ts`:**
```ts
import { EventSink } from "./eventSink";
import { OpenObserveSink } from "./openObserveSink";
import { logInfo, logError } from "./logger";

export function createEventSink(type: "ux" | "sim"): EventSink {
  const env = process.env;
  const sinkType = type === "ux" ? env.UX_EVENT_SINK_TYPE : env.SIM_EVENT_SINK_TYPE;
  const url = type === "ux" ? env.UX_EVENT_SINK_URL : env.SIM_EVENT_SINK_URL;
  const apiKey = type === "ux" ? env.UX_EVENT_SINK_API_KEY : env.SIM_EVENT_SINK_API_KEY;

  logInfo(`Creating event sink for ${type}: ${sinkType}`);
  switch (sinkType) {
    case "openobserve":
      return new OpenObserveSink(url, apiKey);
    // Add more sink types here as needed
    default:
      logError(`Unknown sink type: ${sinkType}`);
      throw new Error(`Unknown sink type: ${sinkType}`);
  }
}
```

---

### 7. Logging Utility

**In `src/logger.ts`:**
```ts
export function logInfo(message: string, ...args: unknown[]) {
  console.info(`[INFO] ${new Date().toISOString()} - ${message}`, ...args);
}

export function logError(message: string, ...args: unknown[]) {
  console.error(`[ERROR] ${new Date().toISOString()} - ${message}`, ...args);
}
```

---

### 8. Integration & Usage

- Use the factory to select the correct sink for each event type at runtime.
- All event dispatches and sink selections are logged.
- Document `.env` keys, event schema, sink usage, and logging in `README.md`.

---

### Further Considerations

- Enums for `eventType` ensure type safety.
- Design is extensible for new sinks and event types.
- Logging can be swapped for a more advanced system if needed.
``