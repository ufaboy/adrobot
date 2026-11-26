import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'

import { CountryMultiSelect } from '@/components/CountryMultiSelect'
import type { Country } from '@/lib/api'

const countries: Country[] = [
  { code: 'DK', name: 'Denmark' },
  { code: 'DE', name: 'Germany' },
  { code: 'US', name: 'United States' },
]

function Picker({ initial = [] }: { initial?: string[] }) {
  const [value, setValue] = useState(initial)
  return <CountryMultiSelect countries={countries} value={value} onChange={setValue} />
}

const chips = () =>
  screen.queryByRole('list', { name: 'Selected countries' })?.textContent ?? ''

describe('CountryMultiSelect', () => {
  it('types in the field, highlights matches and Enter adds the top match as a chip', async () => {
    const user = userEvent.setup()
    render(<Picker />)
    const input = screen.getByRole('combobox')

    await user.type(input, 'germ')
    expect(screen.getAllByRole('option')).toHaveLength(1)
    expect(screen.getByText('Germ', { selector: 'mark' })).toBeInTheDocument()

    await user.keyboard('{Enter}')
    expect(chips()).toBe('DE')
    // The query is cleared so the next country can be typed right away.
    expect(input).toHaveValue('')
    expect(screen.getAllByRole('option')).toHaveLength(3)
  })

  it('picking a selected country again removes it', async () => {
    const user = userEvent.setup()
    render(<Picker initial={['US']} />)

    await user.type(screen.getByRole('combobox'), 'us')
    await user.keyboard('{Enter}')
    expect(chips()).toBe('')
  })

  it('Backspace on an empty input removes the last chip', async () => {
    const user = userEvent.setup()
    render(<Picker initial={['DK', 'US']} />)

    await user.click(screen.getByRole('combobox'))
    await user.keyboard('{Backspace}')
    expect(chips()).toBe('DK')
  })

  it('the chip close button removes that country', async () => {
    const user = userEvent.setup()
    render(<Picker initial={['DK', 'US']} />)

    await user.click(screen.getByRole('button', { name: 'Remove Denmark' }))
    expect(chips()).toBe('US')
  })
})
