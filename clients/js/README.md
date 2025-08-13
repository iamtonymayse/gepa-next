# GEPA TypeScript Client

```ts
import { GepaClient } from 'gepa-client';

const client = new GepaClient('http://localhost:8000', { openrouterKey: 'dev' });
const jobId = await client.createJob('hello world');
for await (const env of client.stream(jobId)) {
  console.log(env.type);
  if (['finished', 'failed', 'cancelled'].includes(env.type)) break;
}
```
