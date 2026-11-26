import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App } from '@/App'
import { renderWithProviders } from '@/test/render'

const renderAt = (path: string) => renderWithProviders(<App />, { path })

describe('App routing', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the campaign list at /', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) =>
        Promise.resolve(
          url.endsWith('/health')
            ? Response.json({ status: 'ok', database: 'ok' })
            : Response.json([{ id: 355, name: 'Spring promo', alias: 'abc', state: 'active' }]),
        ),
      ),
    )

    renderAt('/')

    expect(screen.getByRole('heading', { name: 'Campaigns' })).toBeInTheDocument()
    expect(await screen.findByText('API: online')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Spring promo' })).toHaveAttribute(
      'href',
      '/campaigns/355',
    )
  })

  it('renders the editor with the campaign id from the path', () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    renderAt('/campaigns/355')

    expect(screen.getByRole('heading', { name: 'Campaign #355' })).toBeInTheDocument()
  })
})
