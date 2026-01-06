import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { EventType } from '../src/config';
import { createEventSink } from '../src/eventSinkFactory';
import { EventSink } from '../src/eventSink';

describe('EventSinkFactory', () => {
  const OLD_ENV = process.env;
  beforeEach(() => {
    process.env = { ...OLD_ENV };
    process.env.UX_EVENT_SINK_TYPE = 'openobserve';
    process.env.UX_EVENT_SINK_URL = 'http://localhost:5080';
    process.env.UX_EVENT_SINK_API_KEY = 'test-key';
    process.env.SIM_EVENT_SINK_TYPE = 'openobserve';
    process.env.SIM_EVENT_SINK_URL = 'http://localhost:5081';
    process.env.SIM_EVENT_SINK_API_KEY = 'sim-key';
  });
  afterEach(() => {
    process.env = OLD_ENV;
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
    delete process.env.UX_EVENT_SINK_URL;
    expect(() => createEventSink(EventType.UX_ACTION)).toThrow();
  });

  it('throws for unknown event type', () => {
    // @ts-expect-error
    expect(() => createEventSink('not_a_type')).toThrow();
  });
});