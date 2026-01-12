import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createEventSink } from '../../src/observability/eventSinkFactory';
import { EventSink, EventType } from '../../src/observability/types';

describe('EventSinkFactory', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_UX_EVENT_SINK_TYPE', 'openobserve');
    vi.stubEnv('VITE_UX_EVENT_SINK_URL', 'http://localhost:5080');
    vi.stubEnv('VITE_UX_EVENT_SINK_API_KEY', 'test-key');
    vi.stubEnv('VITE_SIM_EVENT_SINK_TYPE', 'openobserve');
    vi.stubEnv('VITE_SIM_EVENT_SINK_URL', 'http://localhost:5081');
    vi.stubEnv('VITE_SIM_EVENT_SINK_API_KEY', 'sim-key');
  });
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('creates a UX event sink with correct config', () => {
    const sink: EventSink = createEventSink(EventType.UX_ACTION);
    expect(sink).toBeInstanceOf(Object);
    expect(sink.constructor.name).toBe('OpenObserveSink');
  });

  it('creates a SIM event sink with correct config', () => {
    const sink: EventSink = createEventSink(EventType.SIMULATION_EVENT);
    expect(sink).toBeInstanceOf(Object);
    expect(sink.constructor.name).toBe('OpenObserveSink');
  });

  it('throws if env is missing', () => {
    vi.stubEnv('VITE_UX_EVENT_SINK_URL', '');
    expect(() => createEventSink(EventType.UX_ACTION)).toThrow();
  });

  it('throws for unknown event type', () => {
    // @ts-expect-error
    expect(() => createEventSink('not_a_type')).toThrow();
  });
});