import { describe, expect, it } from 'vitest'

import type { Country } from '@/lib/api'
import { searchCountries } from '@/lib/country-search'

const countries: Country[] = [
  { code: 'BD', name: 'Bangladesh' },
  { code: 'CV', name: 'Cabo Verde' },
  { code: 'CD', name: 'Congo, The Democratic Republic of the' },
  { code: 'DK', name: 'Denmark' },
  { code: 'DE', name: 'Germany' },
  { code: 'FM', name: 'Micronesia, Federated States of' },
  { code: 'GB', name: 'United Kingdom' },
  { code: 'US', name: 'United States' },
]

const codes = (query: string) => searchCountries(countries, query).map((c) => c.code)

describe('searchCountries', () => {
  it('returns every country for an empty query', () => {
    expect(codes('  ')).toHaveLength(countries.length)
  })

  it('ranks an exact code first, then name prefix, then word prefix, then substring', () => {
    // Germany (code), Denmark (name prefix), Democratic (word prefix),
    // then mid-word substrings in list order: Bangla-de-sh, Ver-de, Fe-de-rated.
    expect(codes('de')).toEqual(['DE', 'DK', 'CD', 'BD', 'CV', 'FM'])
  })

  it('does not fuzzy-match scattered letters', () => {
    expect(codes('gmy')).toEqual([])
    expect(codes('dnk')).toEqual([])
  })

  it('matches names case-insensitively and by any word', () => {
    expect(codes('KINGDOM')).toEqual(['GB'])
    expect(codes('united')).toEqual(['GB', 'US'])
  })
})
