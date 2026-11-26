import type { Country } from '@/lib/api'

/**
 * Countries matching `query`: the ISO code starts with it, or the name contains it.
 * Results are ranked so the most likely pick comes first:
 * exact code, name prefix, code prefix, word prefix in the name, any substring.
 */
export function searchCountries(countries: Country[], query: string): Country[] {
  const q = query.trim().toLowerCase()
  if (!q) return countries

  const rank = (country: Country): number => {
    const code = country.code.toLowerCase()
    const name = country.name.toLowerCase()
    if (code === q) return 0
    if (name.startsWith(q)) return 1
    if (code.startsWith(q)) return 2
    if (name.split(/[\s,()'-]+/).some((word) => word.startsWith(q))) return 3
    if (name.includes(q)) return 4
    return -1
  }

  return countries
    .map((country, index) => ({ country, index, rank: rank(country) }))
    .filter((entry) => entry.rank >= 0)
    .sort((a, b) => a.rank - b.rank || a.index - b.index)
    .map((entry) => entry.country)
}
