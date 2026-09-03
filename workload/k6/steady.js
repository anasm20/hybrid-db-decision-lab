import http from 'k6/http';
import { check, sleep } from 'k6';

const base = __ENV.BASE_URL || 'http://localhost:8080';
const runId = __ENV.RUN_ID || 'manual';

export const options = {
  scenarios: {
    steady: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS || 25),
      duration: __ENV.DURATION || '3m',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<500'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
  tags: { run_id: runId, scenario: 'steady' },
};

export default function () {
  const id = `${runId}-${__VU}-${__ITER}`;
  const r = http.post(`${base}/records`, JSON.stringify({external_id: id, district: (__VU % 23) + 1}), {
    headers: {'Content-Type': 'application/json'},
    tags: {operation: 'create_record'},
  });
  check(r, { 'write accepted': (x) => x.status === 200 });
  const h = http.get(`${base}/health`, {tags: {operation: 'health'}});
  check(h, { 'health ok': (x) => x.status === 200 });
  sleep(0.2);
}
