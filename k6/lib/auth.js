import http from 'k6/http';
import { API, JSON_HEADERS } from './config.js';

export const LOADTEST_PASSWORD = __ENV.LOADTEST_PASSWORD || 'LoadTest123!';
export const LOADTEST_USERS = parseInt(__ENV.LOADTEST_USERS || '200', 10);

// Per-VU cache (each VU has its own JS runtime). Tokens live 15 min; refresh after 10.
const cache = {};

export function userEmail(n) {
  return `loadtest${n}@example.com`;
}

export function login(email, password = LOADTEST_PASSWORD) {
  const res = http.post(`${API}/auth/login`, JSON.stringify({ email, password }), {
    headers: JSON_HEADERS,
    tags: { name: 'POST /auth/login', flow: 'auth' },
  });
  return res.status === 200 ? res.json('access_token') : null;
}

export function cachedLogin(email, password) {
  const entry = cache[email];
  if (entry && entry.expires > Date.now()) return entry.token;
  const token = login(email, password);
  if (token) cache[email] = { token, expires: Date.now() + 10 * 60 * 1000 };
  return token;
}

export function tokenForVu(vu = __VU) {
  return cachedLogin(userEmail(((vu - 1) % LOADTEST_USERS) + 1), LOADTEST_PASSWORD);
}

export function authParams(token, name, flow, extraHeaders = {}) {
  return {
    headers: { ...JSON_HEADERS, Authorization: `Bearer ${token}`, ...extraHeaders },
    tags: { name, flow },
  };
}
