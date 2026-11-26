import type { MutateOptions, UseMutationResult } from '@tanstack/react-query'
import { useRef } from 'react'

/**
 * `mutate` that ignores calls while a previous one is still in flight.
 *
 * Disabling the button is not enough: TanStack Query reports `isPending` to React only
 * after a macrotask, so the second click of a double click arrives while the button is
 * still enabled. A duplicate request either repeats a Keitaro call or fails with a
 * misleading 409 ("already removed", "already in progress") although the first one
 * succeeded. The ref guard drops it synchronously.
 */
export function useSingleFlight<TData, TError, TVariables, TContext>(
  mutation: UseMutationResult<TData, TError, TVariables, TContext>,
) {
  const inFlight = useRef(false)

  return (
    variables: TVariables,
    options?: MutateOptions<TData, TError, TVariables, TContext>,
  ): boolean => {
    if (inFlight.current) return false
    inFlight.current = true
    mutation.reset()
    mutation.mutate(variables, {
      ...options,
      onSettled: (...args) => {
        inFlight.current = false
        return options?.onSettled?.(...args)
      },
    })
    return true
  }
}
