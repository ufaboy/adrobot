import { useState } from 'react'

import { Input } from '@/components/ui/input'

interface ShareInputProps {
  offerId: number
  value: number
  disabled?: boolean
  /** `revert` puts the server's value back, e.g. when the change is rejected. */
  onCommit: (share: number, revert: () => void) => void
}

/** Percent input; commits on blur or Enter only when the value actually changed. */
export function ShareInput({ offerId, value, disabled, onCommit }: ShareInputProps) {
  const [draft, setDraft] = useState(String(value))
  const [synced, setSynced] = useState(value)

  // Reset the draft when the server returns a new value.
  if (synced !== value) {
    setSynced(value)
    setDraft(String(value))
  }

  const commit = () => {
    const parsed = Number(draft)
    if (draft.trim() === '' || !Number.isInteger(parsed) || parsed < 0 || parsed > 100) {
      setDraft(String(value))
      return
    }
    if (parsed !== value) onCommit(parsed, () => setDraft(String(value)))
  }

  return (
    <div className="flex items-center gap-1">
      <Input
        aria-label={`Share of offer ${offerId}`}
        className="h-7 w-16 text-right tabular-nums"
        inputMode="numeric"
        value={draft}
        disabled={disabled}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === 'Enter') event.currentTarget.blur()
          if (event.key === 'Escape') setDraft(String(value))
        }}
      />
      <span className="text-muted-foreground">%</span>
    </div>
  )
}
