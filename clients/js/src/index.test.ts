import { describe, it, expect, vi } from 'vitest';
import { GepaClient } from './index.js';

describe('GepaClient', () => {
  it('creates job', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ json: async () => ({ job_id: '1' }) });
    (globalThis as any).fetch = fetchMock;
    const client = new GepaClient('http://test');
    const job = await client.createJob('hi');
    expect(job).toBe('1');
  });
});
