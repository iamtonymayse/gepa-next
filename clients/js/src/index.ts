export type SSEEnvelope = {
  type: 'started' | 'progress' | 'finished' | 'failed' | 'cancelled' | 'shutdown';
  schema_version: number;
  job_id: string;
  ts: number;
  id?: number;
  data: Record<string, any>;
};

export type JobState = {
  job_id: string;
  status: string;
  created_at: number;
  updated_at: number;
  result?: Record<string, any> | null;
};

const TERMINALS = new Set(['finished', 'failed', 'cancelled', 'shutdown']);

export class GepaClient {
  private bearerToken?: string;
  private openrouterKey?: string;
  private timeout: number;
  private lastIds = new Map<string, number>();

  constructor(
    private baseUrl: string,
    opts: { bearerToken?: string; openrouterKey?: string; timeout?: number } = {}
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.bearerToken = opts.bearerToken;
    this.openrouterKey = opts.openrouterKey;
    this.timeout = opts.timeout ?? 30000;
  }

  private headers(extra: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = { ...extra };
    if (this.bearerToken) headers['Authorization'] = `Bearer ${this.bearerToken}`;
    else if (this.openrouterKey)
      headers['OpenRouter-API-Key'] = this.openrouterKey;
    return headers;
  }

  async createJob(
    prompt: string,
    context?: Record<string, any>,
    iterations?: number,
    idempotencyKey?: string,
    opts: {
      examples?: Array<Record<string, any>>;
      objectives?: string[];
      seed?: number;
      model_id?: string;
      temperature?: number;
      max_tokens?: number;
    } = {}
  ): Promise<string> {
    const headers = this.headers(
      idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}
    );
    headers['Content-Type'] = 'application/json';
    const params = iterations ? `?iterations=${iterations}` : '';
    const body: any = { prompt };
    if (context) body.context = context;
    if (opts.examples) body.examples = opts.examples;
    if (opts.objectives) body.objectives = opts.objectives;
    if (opts.seed !== undefined) body.seed = opts.seed;
    if (opts.model_id) body.model_id = opts.model_id;
    if (opts.temperature !== undefined) body.temperature = opts.temperature;
    if (opts.max_tokens !== undefined) body.max_tokens = opts.max_tokens;
    const resp = await fetch(`${this.baseUrl}/v1/optimize${params}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    const data = await resp.json();
    return data.job_id;
  }

  async state(jobId: string): Promise<JobState> {
    const resp = await fetch(`${this.baseUrl}/v1/optimize/${jobId}`, {
      headers: this.headers(),
    });
    return (await resp.json()) as JobState;
  }

  async cancel(jobId: string): Promise<void> {
    await fetch(`${this.baseUrl}/v1/optimize/${jobId}`, {
      method: 'DELETE',
      headers: this.headers(),
    });
  }

  async *stream(jobId: string, lastEventId?: number): AsyncGenerator<SSEEnvelope> {
    let last = lastEventId ?? this.lastIds.get(jobId) ?? 0;
    let backoff = 100;
    while (true) {
      const headers = this.headers(last ? { 'Last-Event-ID': String(last) } : {});
      try {
        const resp = await fetch(
          `${this.baseUrl}/v1/optimize/${jobId}/events`,
          { headers }
        );
        const reader = resp.body!.getReader();
        const decoder = new TextDecoder();
        let buf = '';
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          let idx;
          while ((idx = buf.indexOf('\n\n')) >= 0) {
            const raw = buf.slice(0, idx);
            buf = buf.slice(idx + 2);
            const dataLine = raw.split('\n').find((l) => l.startsWith('data:'));
            if (!dataLine) continue;
            const env = JSON.parse(dataLine.slice(5).trim()) as SSEEnvelope;
            last = env.id ?? last;
            this.lastIds.set(jobId, last);
            yield env;
            if (TERMINALS.has(env.type)) return;
          }
        }
      } catch {
        /* ignore */
      }
      await new Promise((r) => setTimeout(r, backoff));
      backoff = Math.min(backoff * 2, 5000);
    }
  }

  async *resume(jobId: string): AsyncGenerator<SSEEnvelope> {
    yield* this.stream(jobId, this.lastIds.get(jobId));
  }
}
