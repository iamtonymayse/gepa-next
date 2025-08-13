const EventSource = require('eventsource');

const BASE = process.env.BASE_URL || 'http://localhost:8000';
const TOKEN = process.env.API_BEARER_TOKEN || 'change-me';
const JOB = process.argv[2];
const LAST = process.argv[3];

const headers = {'Authorization': `Bearer ${TOKEN}`};
if (LAST) headers['Last-Event-ID'] = String(LAST);

const es = new EventSource(`${BASE}/v1/optimize/${JOB}/events`, {headers});
es.onmessage = (e) => console.log('message:', e.data);
es.onerror = (e) => console.error('error:', e);
es.addEventListener('finished', (e) => { console.log('finished:', e.data); es.close(); });
