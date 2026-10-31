import { check } from 'k6';

export function expectStatus(res, expected, name) {
  const statuses = Array.isArray(expected) ? expected : [expected];
  return check(res, { [`${name}: status ${statuses.join('|')}`]: (r) => statuses.includes(r.status) });
}

export function randomBetween(min, max) {
  return Math.random() * (max - min) + min;
}

export function pick(items) {
  return items[Math.floor(Math.random() * items.length)];
}

export function pickMany(items, count) {
  const copy = [...items];
  const result = [];
  while (copy.length && result.length < count) {
    result.push(copy.splice(Math.floor(Math.random() * copy.length), 1)[0]);
  }
  return result;
}

export function tagged(name, flow, extra = {}) {
  return { ...extra, tags: { name, flow } };
}
