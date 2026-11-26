import { useSlow } from '@/hooks/use-slow'

/** "Keitaro is responding slowly…" shown while a change has been running for a while. */
export function SlowHint({ pending }: { pending: boolean }) {
  const slow = useSlow(pending)
  if (!slow) return null
  return (
    <span role="status" className="text-sm text-muted-foreground">
      Keitaro is responding slowly… still working.
    </span>
  )
}
