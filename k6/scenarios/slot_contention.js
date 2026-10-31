// Many VUs race for the same slot at the same instant.
// Expected: exactly one 201, every other request 409 (FR-BOOK-05 / NFR-06 evidence).
// Requires load-test users: `make seed-loadtest` (at least CONTENDERS users).
import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';
import { API, JSON_HEADERS } from '../lib/config.js';
import { login, userEmail } from '../lib/auth.js';
import { clinicDate } from '../lib/data.js';

const CONTENDERS = parseInt(__ENV.CONTENDERS || '50', 10);
const created = new Counter('contention_booking_created');
const conflicts = new Counter('contention_booking_conflict');

http.setResponseCallback(http.expectedStatuses({ min: 200, max: 299 }, 409));

export const options = {
  scenarios: {
    race: { executor: 'per-vu-iterations', vus: CONTENDERS, iterations: 1, maxDuration: '1m', exec: 'race' },
  },
  thresholds: {
    contention_booking_created: ['count==1'],
    checks: ['rate==1'],
  },
};

function findSlot() {
  const doctors = http.get(`${API}/doctors?page_size=100`).json('items') || [];
  for (let offset = 13; offset >= 3; offset--) {
    for (const doctor of doctors) {
      const types = http.get(`${API}/doctors/${doctor.id}/appointment-types`).json() || [];
      if (!types.length) continue;
      const slots = http
        .get(`${API}/doctors/${doctor.id}/availability?date=${clinicDate(offset)}&appointment_type_id=${types[0].id}`)
        .json('slots') || [];
      if (slots.length) {
        return { doctorId: doctor.id, typeId: types[0].id, startTime: slots[slots.length - 1].start_time };
      }
    }
  }
  throw new Error('No free slot found for the contention test');
}

export function setup() {
  const tokens = [];
  for (let i = 1; i <= CONTENDERS; i++) {
    const token = login(userEmail(i));
    if (token) tokens.push(token);
  }
  if (tokens.length < CONTENDERS) throw new Error(`Only ${tokens.length}/${CONTENDERS} users could log in - run make seed-loadtest`);
  return { tokens, ...findSlot() };
}

export function race(data) {
  const res = http.post(
    `${API}/appointments`,
    JSON.stringify({ doctor_id: data.doctorId, appointment_type_id: data.typeId, start_time: data.startTime }),
    {
      headers: { ...JSON_HEADERS, Authorization: `Bearer ${data.tokens[(__VU - 1) % data.tokens.length]}` },
      tags: { name: 'POST /appointments (contention)', flow: 'contention' },
    },
  );
  check(res, { 'status is 201 or 409': (r) => r.status === 201 || r.status === 409 });
  if (res.status === 201) created.add(1);
  else if (res.status === 409) conflicts.add(1);
}

export default race;
