import { XIcon } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'

import { HighlightMatch } from '@/components/HighlightMatch'
import { Badge } from '@/components/ui/badge'
import { Command, CommandEmpty, CommandGroup, CommandItem, CommandList } from '@/components/ui/command'
import { useComboboxAria } from '@/hooks/use-combobox-aria'
import type { Country } from '@/lib/api'
import { searchCountries } from '@/lib/country-search'
import { cn } from '@/lib/utils'

interface CountryMultiSelectProps {
  id?: string
  countries: Country[]
  value: string[]
  onChange: (codes: string[]) => void
  invalid?: boolean
}

/**
 * Country multi-select as an inline tag input: selected countries are chips inside
 * the field, the user types a code or name right after them and toggles matches
 * in the list below. Backspace on an empty input removes the last chip.
 */
export function CountryMultiSelect({
  id,
  countries,
  value,
  onChange,
  invalid,
}: CountryMultiSelectProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const names = useMemo(() => new Map(countries.map((c) => [c.code, c.name])), [countries])
  const results = useMemo(() => searchCountries(countries, query), [countries, query])
  const [highlighted, setHighlighted] = useState(countries[0]?.code ?? '')
  useComboboxAria(inputRef, listRef, open)

  const toggle = (code: string) => {
    onChange(value.includes(code) ? value.filter((c) => c !== code) : [...value, code])
  }

  function search(next: string) {
    setQuery(next)
    setOpen(true)
    // A new query starts from the top: highlight and show the best match.
    setHighlighted(searchCountries(countries, next)[0]?.code ?? '')
    if (listRef.current) listRef.current.scrollTop = 0
  }

  function pick(code: string) {
    toggle(code)
    if (query) search('')
  }

  return (
    <Command
      shouldFilter={false}
      value={highlighted}
      onValueChange={setHighlighted}
      className="relative overflow-visible bg-transparent p-0"
      onKeyDown={(event) => {
        if (event.key === 'Escape' && open) {
          event.preventDefault()
          setOpen(false)
        } else if (event.key === 'ArrowDown' && !open) {
          setOpen(true)
        } else if (event.key === 'Backspace' && !query && value.length > 0) {
          onChange(value.slice(0, -1))
        }
      }}
    >
      {/* Looks like a single input; clicking anywhere in it focuses the real input. */}
      <div
        data-invalid={invalid || undefined}
        onMouseDown={(event) => {
          if (event.target !== inputRef.current) {
            event.preventDefault()
            inputRef.current?.focus()
          }
        }}
        className={cn(
          'flex min-h-8 w-full cursor-text flex-wrap items-center gap-1 rounded-lg border border-input bg-transparent px-1.5 py-1 transition-colors dark:bg-input/30',
          'focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50',
          'data-invalid:border-destructive data-invalid:ring-3 data-invalid:ring-destructive/20',
        )}
      >
        {value.length > 0 && (
          <ul className="contents" aria-label="Selected countries">
            {value.map((code) => (
              <li key={code}>
                <Badge variant="secondary" className="gap-1 pr-1" title={names.get(code)}>
                  {code}
                  <button
                    type="button"
                    tabIndex={-1}
                    className="cursor-pointer rounded-sm opacity-60 hover:opacity-100"
                    aria-label={`Remove ${names.get(code) ?? code}`}
                    onClick={() => toggle(code)}
                  >
                    <XIcon className="size-3" />
                  </button>
                </Badge>
              </li>
            ))}
          </ul>
        )}
        <input
          ref={inputRef}
          id={id}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-autocomplete="list"
          value={query}
          onChange={(event) => search(event.target.value)}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          placeholder={value.length ? '' : 'Type country code or name…'}
          autoComplete="off"
          spellCheck={false}
          aria-invalid={invalid}
          className="h-6 min-w-24 flex-1 bg-transparent px-1 text-sm outline-none placeholder:text-muted-foreground"
        />
      </div>

      {open && (
        <div
          className="absolute inset-x-0 top-full z-50 mt-1 rounded-lg border bg-popover p-1 text-popover-foreground shadow-md"
          // Keep focus in the input while clicking a result.
          onMouseDown={(event) => event.preventDefault()}
        >
          <CommandList ref={listRef}>
            <CommandEmpty>No countries found.</CommandEmpty>
            <CommandGroup>
              {results.map((country) => (
                <CommandItem
                  key={country.code}
                  value={country.code}
                  data-checked={value.includes(country.code)}
                  onSelect={() => pick(country.code)}
                >
                  <span className="w-7 font-mono text-xs text-muted-foreground">
                    <HighlightMatch
                      text={country.code}
                      query={country.code.toLowerCase().startsWith(query.trim().toLowerCase()) ? query : ''}
                    />
                  </span>
                  <span className="truncate">
                    <HighlightMatch text={country.name} query={query} />
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </div>
      )}
    </Command>
  )
}
