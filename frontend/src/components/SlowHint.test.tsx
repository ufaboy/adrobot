import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { LoadError } from '@/components/LoadError'
import { SlowHint } from '@/components/SlowHint'

describe('SlowHint', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('appears only after a change has been pending for 5 seconds', () => {
    const { rerender } = render(<SlowHint pending />)

    act(() => vi.advanceTimersByTime(4900))
    expect(screen.queryByRole('status')).not.toBeInTheDocument()

    act(() => vi.advanceTimersByTime(200))
    expect(screen.getByRole('status')).toHaveTextContent('Keitaro is responding slowly')

    rerender(<SlowHint pending={false} />)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})

describe('LoadError', () => {
  it('shows the error and retries on click', async () => {
    const onRetry = vi.fn()
    render(
      <LoadError
        title="Could not load campaigns"
        error={new Error('Keitaro: request timed out')}
        onRetry={onRetry}
        retrying={false}
      />,
    )

    expect(screen.getByText('Keitaro: request timed out')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledOnce()
  })
})
