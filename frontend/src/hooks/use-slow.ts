import { useEffect, useState } from 'react'

/** True once `pending` has stayed true for `afterMs`; resets when it turns false. */
export function useSlow(pending: boolean, afterMs = 5000): boolean {
  const [slow, setSlow] = useState(false)

  useEffect(() => {
    if (!pending) return
    const timer = setTimeout(() => setSlow(true), afterMs)
    return () => {
      clearTimeout(timer)
      setSlow(false)
    }
  }, [pending, afterMs])

  return pending && slow
}
