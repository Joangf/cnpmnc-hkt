export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
export const API = `${BASE_URL}/api/v1`;
export const JSON_HEADERS = { 'Content-Type': 'application/json' };

// Clinic timezone offset (Asia/Ho_Chi_Minh has no DST).
export const CLINIC_UTC_OFFSET_HOURS = parseInt(__ENV.CLINIC_UTC_OFFSET_HOURS || '7', 10);
