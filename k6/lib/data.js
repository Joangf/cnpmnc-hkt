import http from 'k6/http';
import { API, CLINIC_UTC_OFFSET_HOURS } from './config.js';

// Called from setup(): discover seeded IDs instead of hard-coding them.
export function loadSeedData() {
  const hospitals = http.get(`${API}/hospitals?page_size=100`).json('items') || [];
  const doctors = http.get(`${API}/doctors?page_size=100`).json('items') || [];
  const symptoms = http.get(`${API}/symptoms`).json() || [];
  if (!doctors.length) throw new Error('No doctors found - is the stack seeded?');
  return {
    hospitalIds: hospitals.map((h) => h.id),
    doctorIds: doctors.map((d) => d.id),
    symptomIds: symptoms.map((s) => s.id),
  };
}

// YYYY-MM-DD in the clinic timezone, offsetDays from today.
export function clinicDate(offsetDays) {
  const shifted = new Date(Date.now() + CLINIC_UTC_OFFSET_HOURS * 3600 * 1000 + offsetDays * 86400 * 1000);
  return shifted.toISOString().slice(0, 10);
}
