import { GepaClient } from '../clients/js/dist/index.js';

const client = new GepaClient('http://localhost:8000', { openrouterKey: 'dev' });
const jobId = await client.createJob('hello world', undefined, undefined, 'demo');
let last;
for await (const env of client.stream(jobId)) {
  last = env;
  if (['finished', 'failed', 'cancelled'].includes(env.type)) break;
}
console.log(last);
