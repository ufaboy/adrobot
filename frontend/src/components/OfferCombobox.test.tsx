import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { OfferCombobox } from '@/components/OfferCombobox'
import { api, type Offer } from '@/lib/api'
import { renderWithProviders } from '@/test/render'

const offer = (id: number, name: string): Offer => ({ id, name, state: 'active', countries: [] })

const catalog = [
  offer(40, 'Beta'),
  offer(30, 'Cardio Max'),
  offer(20, 'Cardio Plus'),
  offer(10, 'Alpha'),
]

/** Controlled wrapper, like the real forms. */
function Picker({ onChange }: { onChange: (offer: Offer | null) => void }) {
  const [value, setValue] = useState<Offer | null>(null)
  return (
    <OfferCombobox
      value={value}
      onChange={(next) => {
        setValue(next)
        onChange(next)
      }}
    />
  )
}

describe('OfferCombobox', () => {
  beforeEach(() => {
    vi.spyOn(api, 'searchOffers').mockImplementation((query) =>
      Promise.resolve(catalog.filter((o) => o.name.toLowerCase().includes(query.toLowerCase()))),
    )
  })
  afterEach(() => vi.restoreAllMocks())

  it('suggests offers while typing in the field and highlights the match', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Picker onChange={vi.fn()} />)

    await user.type(screen.getByRole('combobox'), 'cardio')

    await vi.waitFor(() => expect(screen.getAllByRole('option')).toHaveLength(2))
    expect(screen.queryByText('Beta')).not.toBeInTheDocument()
    const marks = screen.getAllByText('Cardio', { selector: 'mark' })
    expect(marks).toHaveLength(2)
    expect(api.searchOffers).toHaveBeenLastCalledWith('cardio')
  })

  it('Enter picks the top result of the latest list and fills the field', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    renderWithProviders(<Picker onChange={onChange} />)
    const input = screen.getByRole('combobox')

    // First query: "Cardio Plus" is the only result and gets highlighted.
    await user.type(input, 'plus')
    await vi.waitFor(() => expect(screen.getAllByRole('option')).toHaveLength(1))

    // Second query: "Cardio Plus" is still listed, but no longer first.
    await user.clear(input)
    await user.type(input, 'cardio')
    await vi.waitFor(() => expect(screen.getAllByRole('option')).toHaveLength(2))

    await user.keyboard('{Enter}')
    expect(onChange).toHaveBeenLastCalledWith(catalog[1])
    expect(input).toHaveValue('Cardio Max')
    expect(screen.queryByRole('option')).not.toBeInTheDocument()
  })

  it('ignores Enter until results for the typed query have arrived', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    renderWithProviders(<Picker onChange={onChange} />)
    const input = screen.getByRole('combobox')

    await user.click(input)
    await vi.waitFor(() => expect(screen.getAllByRole('option')).toHaveLength(4))

    // Enter right after typing: the list still shows the unfiltered results.
    await user.type(input, 'alpha{Enter}')
    expect(onChange).not.toHaveBeenCalled()

    await vi.waitFor(() => expect(screen.getAllByRole('option')).toHaveLength(1))
    await user.keyboard('{Enter}')
    expect(onChange).toHaveBeenLastCalledWith(catalog[3])
  })

  it('typing over a picked offer clears the selection', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    renderWithProviders(<Picker onChange={onChange} />)
    const input = screen.getByRole('combobox')

    await user.type(input, 'alpha')
    await vi.waitFor(() => expect(screen.getAllByRole('option')).toHaveLength(1))
    await user.keyboard('{Enter}')
    expect(input).toHaveValue('Alpha')

    await user.type(input, 'x')
    expect(onChange).toHaveBeenLastCalledWith(null)
  })
})
