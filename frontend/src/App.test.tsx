import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App } from '@/App'

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('App routing', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the campaign list at /', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(Response.json({ status: 'ok', database: 'ok' })),
    )

    renderAt('/')

    expect(screen.getByRole('heading', { name: 'Campaigns' })).toBeInTheDocument()
    expect(await screen.findByText('API: online')).toBeInTheDocument()
  })

  it('renders the editor with the campaign id from the path', () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    renderAt('/campaigns/355')

    expect(screen.getByRole('heading', { name: 'Campaign #355' })).toBeInTheDocument()
  })
})
