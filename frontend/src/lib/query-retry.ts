import { NetworkError } from '@/lib/api'

/**
 * TanStack Query retry rule: retry once, and only when the backend was not reached at all.
 *
 * An error response from the backend (e.g. 502/503 from Keitaro) is not retried: the
 * backend already retried Keitaro where it was safe, and every extra attempt shows up
 * in the Keitaro API journal.
 */
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  return error instanceof NetworkError && failureCount < 1
}
