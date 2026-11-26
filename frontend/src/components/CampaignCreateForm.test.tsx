import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { CampaignCreateForm } from '@/components/CampaignCreateForm'
import type { ReferenceData } from '@/lib/api'
import { renderWithProviders } from '@/test/render'

const reference: ReferenceData = {
  domains: [{ id: 1813, name: 'kt-emulator.test' }],
  groups: [{ id: 10332, name: 'FORTESTS' }],
  traffic_sources: [{ id: 836, name: 'FORTESTS' }],
  countries: [
    { code: 'AU', name: 'Australia' },
    { code: 'MX', name: 'Mexico' },
  ],
  defaults: { domain_id: 1813, group_id: 10332, traffic_source_id: 836 },
}

describe('CampaignCreateForm', () => {
  it('shows validation errors and does not submit an empty form', async () => {
    const onSubmit = vi.fn()
    renderWithProviders(
      <CampaignCreateForm
        reference={reference}
        onSubmit={onSubmit}
        isSubmitting={false}
        submitError={null}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Create campaign' }))

    expect(await screen.findByText('Name is required')).toBeInTheDocument()
    expect(screen.getByText('Select at least one country')).toBeInTheDocument()
    expect(screen.getByText('Select an offer')).toBeInTheDocument()
    // Reference defaults pre-fill the selects, so they are valid.
    expect(screen.queryByText('Select a domain')).not.toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('links the Geo and Offer labels to their autocomplete inputs', () => {
    renderWithProviders(
      <CampaignCreateForm
        reference={reference}
        onSubmit={vi.fn()}
        isSubmitting={false}
        submitError={null}
      />,
    )

    for (const label of ['Geo', 'Offer']) {
      const input = screen.getByLabelText(label)
      expect(input).toHaveRole('combobox')
      expect(input).toHaveAttribute('aria-expanded', 'false')
    }
  })

  it('shows the server error returned on submit', () => {
    renderWithProviders(
      <CampaignCreateForm
        reference={reference}
        onSubmit={vi.fn()}
        isSubmitting={false}
        submitError="Keitaro: offers: offer 1 does not exist"
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Keitaro: offers: offer 1 does not exist')
  })
})
