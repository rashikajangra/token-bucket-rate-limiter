import http from 'k6/http';
import { Counter } from 'k6/metrics';

const allowed = new Counter('allowed_count');
const denied = new Counter('denied_count');
const errors = new Counter('error_count');

export const options = {
  vus: 500,
  duration: '10s',
};

export default function () {
  const res = http.get('http://127.0.0.1:8000/check', {
    headers: { 'X-Client-Id': 'loadtest_client' },
  });

  if (res.status === 200) allowed.add(1);
  else if (res.status === 429) denied.add(1);
  else errors.add(1);
}