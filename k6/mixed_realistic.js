// Weighted, time-varying mix: ~70% browse, 15% symptom checker, 12% booking, 3% admin.
// ramping-arrival-rate models daily peaks (iterations/minute), independent of response time.
//
//   PEAK_PER_MIN=600 make loadtest            (default 600 iterations/min at peak)
import http from 'k6/http';
import { guestBrowse } from './scenarios/guest_browse.js';
import { symptomFlow } from './scenarios/symptom_flow.js';
import { patientBooking } from './scenarios/patient_booking.js';
import { adminOps } from './scenarios/admin_ops.js';
import { loadSeedData } from './lib/data.js';

http.setResponseCallback(http.expectedStatuses({ min: 200, max: 299 }, 409));

const PEAK = parseInt(__ENV.PEAK_PER_MIN || '600', 10);
// TIME_SCALE=0.1 compresses the 13-minute profile to ~80 s for smoke runs / CI.
const TIME_SCALE = parseFloat(__ENV.TIME_SCALE || '1');
const thresholds = JSON.parse(open('./thresholds.json'));

// Morning ramp, peak, lunch dip, afternoon peak, wind-down.
function stages(share) {
  const at = (fraction) => Math.max(1, Math.round(PEAK * share * fraction));
  const minutes = (m) => `${Math.max(5, Math.round(m * 60 * TIME_SCALE))}s`;
  return [
    { duration: minutes(2), target: at(0.3) },
    { duration: minutes(3), target: at(1.0) },
    { duration: minutes(3), target: at(1.0) },
    { duration: minutes(2), target: at(0.4) },
    { duration: minutes(2), target: at(1.0) },
    { duration: minutes(1), target: at(0.1) },
  ];
}

function scenario(exec, share, maxVUs) {
  return {
    executor: 'ramping-arrival-rate',
    exec,
    startRate: 1,
    timeUnit: '1m',
    preAllocatedVUs: Math.ceil(maxVUs / 4),
    maxVUs,
    stages: stages(share),
  };
}

export const options = {
  scenarios: {
    guest_browse: scenario('browse', 0.7, 300),
    symptom_flow: scenario('symptom', 0.15, 80),
    patient_booking: scenario('booking', 0.12, 80),
    admin_ops: scenario('admin', 0.03, 10),
  },
  thresholds,
};

export function setup() {
  return loadSeedData();
}

export function browse(data) {
  guestBrowse(data);
}

export function symptom(data) {
  symptomFlow(data);
}

export function booking(data) {
  patientBooking(data);
}

export function admin() {
  adminOps();
}
