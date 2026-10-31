// Patient: login -> availability -> book -> pay (mock) -> view -> sometimes cancel.
// Requires load-test users: `make seed-loadtest`.
import http from 'k6/http';
import { sleep } from 'k6';
import { API, BASE_URL, JSON_HEADERS } from '../lib/config.js';
import { authParams, tokenForVu } from '../lib/auth.js';
import { expectStatus, pick, randomBetween, tagged } from '../lib/checks.js';
import { clinicDate, loadSeedData } from '../lib/data.js';

// 409 (slot taken) is an expected business outcome, not a failed request.
http.setResponseCallback(http.expectedStatuses({ min: 200, max: 299 }, 409));

export const options = {
  scenarios: {
    patient_booking: { executor: 'constant-vus', vus: 5, duration: '2m', exec: 'patientBooking' },
  },
  thresholds: { 'http_req_duration{flow:booking}': ['p(99)<1000'], http_req_failed: ['rate<0.01'] },
};

export function setup() {
  return loadSeedData();
}

export function patientBooking(data) {
  const token = tokenForVu();
  if (!token) {
    sleep(1);
    return;
  }
  const p = (name, extra) => authParams(token, name, 'booking', extra);

  const doctorId = pick(data.doctorIds);
  const types = http.get(`${API}/doctors/${doctorId}/appointment-types`, tagged('GET /doctors/{id}/appointment-types', 'booking'));
  const typeList = types.json() || [];
  if (!typeList.length) return;
  const type = pick(typeList);

  // Days 2-13 so cancellation (24h cut-off) remains possible.
  const date = clinicDate(Math.floor(randomBetween(2, 14)));
  const avail = http.get(
    `${API}/doctors/${doctorId}/availability?date=${date}&appointment_type_id=${type.id}`,
    tagged('GET /doctors/{id}/availability', 'booking'),
  );
  const slots = avail.json('slots') || [];
  if (!slots.length) return;
  sleep(randomBetween(1, 3));

  const slot = pick(slots);
  const booking = http.post(
    `${API}/appointments`,
    JSON.stringify({ doctor_id: doctorId, appointment_type_id: type.id, start_time: slot.start_time, reason_for_visit: 'Load test' }),
    p('POST /appointments', { 'Idempotency-Key': `k6-${__VU}-${__ITER}-${Date.now()}` }),
  );
  expectStatus(booking, [201, 409], 'create appointment');
  if (booking.status !== 201) return;

  const appointment = booking.json();
  sleep(randomBetween(1, 3));

  if (appointment.can_pay) {
    const init = http.post(`${API}/appointments/${appointment.id}/payments`, null, p('POST /appointments/{id}/payments'));
    expectStatus(init, 201, 'initiate payment');
    if (init.status === 201) {
      const ref = init.json('checkout_url').split('/').pop();
      const outcome = Math.random() < 0.9 ? 'success' : 'fail';
      http.post(`${BASE_URL}/mock-payment/api/checkouts/${ref}/simulate`, JSON.stringify({ outcome }), {
        headers: JSON_HEADERS,
        tags: { name: 'mock checkout simulate', flow: 'gateway' },
      });
      expectStatus(http.get(`${API}/payments/${init.json('payment_id')}`, p('GET /payments/{id}')), 200, 'payment result');
    }
  }

  expectStatus(http.get(`${API}/appointments/${appointment.id}`, p('GET /appointments/{id}')), 200, 'view appointment');
  expectStatus(http.get(`${API}/appointments?scope=upcoming`, p('GET /appointments')), 200, 'list appointments');

  // Free most slots again so long runs don't exhaust capacity.
  if (Math.random() < 0.7) {
    sleep(randomBetween(1, 2));
    const cancel = http.post(
      `${API}/appointments/${appointment.id}/cancel`,
      JSON.stringify({ reason: 'Load test cleanup' }),
      p('POST /appointments/{id}/cancel'),
    );
    expectStatus(cancel, [200, 409], 'cancel appointment');
  }
  sleep(randomBetween(1, 5));
}

export default patientBooking;
