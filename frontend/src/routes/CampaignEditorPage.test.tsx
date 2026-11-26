import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { CampaignCreated } from '@/lib/api'
import { CampaignEditorPage } from '@/routes/CampaignEditorPage'

const created: CampaignCreated = {
  id: 521,
  name: 'Spring promo',
  alias: 'abc',
  geo: ['DE'],
  offer_id: 18170,
  stream_ids: [924, 925],
}

/** Renders the current history state, so the test can see it being cleared. */
function LocationProbe() {
  return <output data-testid="location-state">{JSON.stringify(useLocation().state)}</output>
}

describe('CampaignEditorPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the creation banner once and clears it from history state', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[{ pathname: '/campaigns/521', state: { created } }]}>
          <Routes>
            <Route path="/campaigns/:id" element={<CampaignEditorPage />} />
          </Routes>
          <LocationProbe />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    // The banner stays for this visit, but a reload would no longer see the state.
    expect(screen.getByText('Campaign “Spring promo” created')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('location-state')).toHaveTextContent('null'))
    expect(screen.getByText('Campaign “Spring promo” created')).toBeInTheDocument()
  })
})
