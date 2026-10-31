// Symptom checker: pick symptoms -> recommendations -> browse doctors of a matched department.
import http from 'k6/http';
import { sleep } from 'k6';
import { API, JSON_HEADERS } from '../lib/config.js';
import { expectStatus, pick, pickMany, randomBetween, tagged } from '../lib/checks.js';
import { loadSeedData } from '../lib/data.js';

export const options = {
  scenarios: {
    symptom_flow: { executor: 'constant-vus', vus: 5, duration: '2m', exec: 'symptomFlow' },
  },
  thresholds: { 'http_req_duration{flow:symptom}': ['p(95)<400'], http_req_failed: ['rate<0.01'] },
};

export function setup() {
  return loadSeedData();
}

export function symptomFlow(data) {
  const p = (name) => tagged(name, 'symptom', { headers: JSON_HEADERS });

  expectStatus(http.get(`${API}/symptoms`, p('GET /symptoms')), 200, 'list symptoms');
  sleep(randomBetween(2, 5));

  const body = JSON.stringify({ symptom_ids: pickMany(data.symptomIds, 1 + Math.floor(randomBetween(0, 3))) });
  const rec = http.post(`${API}/symptoms/recommendations`, body, p('POST /symptoms/recommendations'));
  expectStatus(rec, 200, 'recommendations');
  const departments = rec.json('departments') || [];
  if (!departments.length) return;
  sleep(randomBetween(1, 3));

  const department = pick(departments);
  const doctors = http.get(`${API}/doctors?department_id=${department.department_id}`, p('GET /doctors'));
  expectStatus(doctors, 200, 'doctors for department');
  const items = doctors.json('items') || [];
  if (items.length) {
    expectStatus(http.get(`${API}/doctors/${pick(items).id}`, p('GET /doctors/{id}')), 200, 'doctor detail');
  }
  sleep(randomBetween(1, 4));
}

export default symptomFlow;
