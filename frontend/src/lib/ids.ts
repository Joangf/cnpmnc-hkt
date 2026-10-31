/** Idempotency key. crypto.randomUUID needs a secure context, getRandomValues does not. */
export function newIdempotencyKey(): string {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
}
