// Guest: hospitals -> hospital detail -> doctors -> doctor detail (+ reviews, availability).
import http from 'k6/http';
import { sleep } from 'k6';
import { API } from '../lib/config.js';
import { expectStatus, pick, randomBetween, tagged } from '../lib/checks.js';
import { clinicDate, loadSeedData } from '../lib/data.js';

export const options = {
  scenarios: {
    guest_browse: { executor: 'constant-vus', vus: 10, duration: '2m', exec: 'guestBrowse' },
  },
  thresholds: { 'http_req_duration{flow:browse}': ['p(95)<300'], http_req_failed: ['rate<0.01'] },
};

export function setup() {
  return loadSeedData();
}

export function guestBrowse(data) {
  const p = (name) => tagged(name, 'browse');

  expectStatus(http.get(`${API}/hospitals?page=1&page_size=20`, p('GET /hospitals')), 200, 'list hospitals');
  sleep(randomBetween(1, 3));

  const hospitalId = pick(data.hospitalIds);
  expectStatus(http.get(`${API}/hospitals/${hospitalId}`, p('GET /hospitals/{id}')), 200, 'hospital detail');
  sleep(randomBetween(1, 3));

  const doctors = http.get(`${API}/doctors?hospital_id=${hospitalId}&page_size=20`, p('GET /doctors'));
  expectStatus(doctors, 200, 'list doctors');
  const items = doctors.json('items') || [];
  if (!items.length) return;
  sleep(randomBetween(1, 3));

  const doctorId = pick(items).id;
  expectStatus(http.get(`${API}/doctors/${doctorId}`, p('GET /doctors/{id}')), 200, 'doctor detail');
  expectStatus(http.get(`${API}/doctors/${doctorId}/reviews`, p('GET /doctors/{id}/reviews')), 200, 'doctor reviews');

  const types = http.get(`${API}/doctors/${doctorId}/appointment-types`, p('GET /doctors/{id}/appointment-types'));
  expectStatus(types, 200, 'appointment types');
  const typeList = types.json() || [];
  if (typeList.length) {
    const url = `${API}/doctors/${doctorId}/availability?date=${clinicDate(Math.floor(randomBetween(1, 7)))}&appointment_type_id=${typeList[0].id}`;
    expectStatus(http.get(url, p('GET /doctors/{id}/availability')), 200, 'availability');
  }
  sleep(randomBetween(1, 5));
}

export default guestBrowse;
