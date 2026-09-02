import http from 'k6/http';
import { check, sleep } from 'k6';
export const options = {
  stages: [
    { duration: '30s', target: 20 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 0 },
  ],
  thresholds: { http_req_failed: ['rate<0.05'], http_req_duration: ['p(95)<500'] },
};
const BASE = __ENV.BASE_URL || 'http://localhost:8000';
export function setup(){
  // obtain JWT
  const res = http.post(`${BASE}/api/auth/token/`, JSON.stringify({username:'admin', password:'admin'}), {headers:{'Content-Type':'application/json'}});
  return { token: res.json('access') };
}
export default function(data){
  const headers = data.token ? {Authorization: `Bearer ${data.token}`} : {};
  let r = http.get(`${BASE}/api/documents/?page_size=20`, {headers});
  check(r, {'GET /api/documents 200': x=> x.status===200});
  r = http.get(`${BASE}/api/processing/search/?q=election&size=10`, {headers});
  check(r, {'GET /api/search 200': x=> x.status===200});
  r = http.get(`${BASE}/health/`);
  check(r, {'GET /health 200': x=> x.status===200});
  sleep(1);
}
