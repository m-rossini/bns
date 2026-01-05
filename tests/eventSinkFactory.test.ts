// eventSinkFactory.test.ts
// TDD: EventSink factory tests
import { describe, it, expect } from 'vitest';
import { createEventSink } from '../src/eventSinkFactory';

describe('createEventSink', () => {
  it('should create OpenObserveSink for ux', () => {
    process.env.UX_EVENT_SINK_TYPE = 'openobserve';
    process.env.UX_EVENT_SINK_URL = 'http://fake-url';
    process.env.UX_EVENT_SINK_API_KEY = 'fake-key';
    const sink = createEventSink('ux');
    expect(sink).toBeDefined();
  });
  it('should throw for unknown sink type', () => {
    process.env.UX_EVENT_SINK_TYPE = 'unknown';
    expect(() => createEventSink('ux')).toThrow();
  });
});