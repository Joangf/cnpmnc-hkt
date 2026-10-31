// Light admin traffic: dashboards, listings, moderation queue.
import http from 'k6/http';
import { sleep } from 'k6';
import { API } from '../lib/config.js';
import { authParams, cachedLogin } from '../lib/auth.js';
import { expectStatus, randomBetween } from '../lib/checks.js';

const ADMIN_EMAIL = __ENV.ADMIN_EMAIL || 'admin@example.com';
const ADMIN_PASSWORD = __ENV.ADMIN_PASSWORD || 'Admin12345!';

export const options = {
  scenarios: {
    admin_ops: { executor: 'constant-vus', vus: 1, duration: '2m', exec: 'adminOps' },
  },
};

export function adminOps() {
  const token = cachedLogin(ADMIN_EMAIL, ADMIN_PASSWORD);
  if (!token) {
    sleep(5);
    return;
  }
  const p = (name) => authParams(token, name, 'admin');
  expectStatus(http.get(`${API}/admin/reports/summary`, p('GET /admin/reports/summary')), 200, 'report summary');
  sleep(randomBetween(2, 5));
  expectStatus(http.get(`${API}/admin/appointments?page_size=20`, p('GET /admin/appointments')), 200, 'admin appointments');
  sleep(randomBetween(2, 5));
  expectStatus(http.get(`${API}/admin/reviews?page_size=20`, p('GET /admin/reviews')), 200, 'admin reviews');
  expectStatus(http.get(`${API}/admin/users?page_size=20`, p('GET /admin/users')), 200, 'admin users');
  sleep(randomBetween(3, 8));
}

export default adminOps;
