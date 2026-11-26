import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ShareInput } from '@/components/editor/ShareInput'

describe('ShareInput', () => {
  it('shows the server value again when a committed share is rejected', async () => {
    const onCommit = vi.fn<(share: number, revert: () => void) => void>()
    render(<ShareInput offerId={7} value={25} onCommit={onCommit} />)
    const input = screen.getByRole('textbox', { name: 'Share of offer 7' })

    await userEvent.clear(input)
    await userEvent.type(input, '30{Enter}')
    expect(onCommit).toHaveBeenCalledWith(30, expect.any(Function))
    expect(input).toHaveValue('30')

    // The backend refused it (e.g. pinned shares above 100%).
    const [, revert] = onCommit.mock.calls[0]
    revert()

    expect(await screen.findByDisplayValue('25')).toBe(input)
  })
})
