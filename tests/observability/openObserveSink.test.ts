import { describe, it, expect, vi, beforeEach } from 'vitest';
import { OpenObserveSink } from '@/observability/openObserveSink';
import { EventType, Event } from '@/observability/types';

describe('OpenObserveSink', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  it('should send event via fetch with correct headers and body', async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
    } as Response);

    const url = 'http://fake-url';
    const apiKey = 'Basic fake-key';
    const sink = new OpenObserveSink(url, apiKey);
    
    const event: Event = {
      id: 'test-id',
      timestamp: '2026-01-11T10:00:00Z',
      eventType: EventType.SIMULATION_EVENT,
      payload: { sim: 1 },
    };

    await sink.sendEvent(event);

    expect(mockFetch).toHaveBeenCalledWith(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': apiKey,
      },
      body: JSON.stringify(event),
    });
  });

  it('should log error when fetch fails', async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Internal Server Error'),
    } as Response);

    const sink = new OpenObserveSink('http://fake-url', 'fake-key');
    const event: Event = {
      id: 'test-id',
      timestamp: '2026-01-11T10:00:00Z',
      eventType: EventType.SIMULATION_EVENT,
      payload: { sim: 1 },
    };

    // Should not throw because we catch it internally
    await expect(sink.sendEvent(event)).resolves.toBeUndefined();
  });
});