import { RefreshCwIcon } from 'lucide-react'
import { useRef, useState } from 'react'

import { HighlightMatch } from '@/components/HighlightMatch'
import { Button } from '@/components/ui/button'
import { Command, CommandEmpty, CommandGroup, CommandItem, CommandList } from '@/components/ui/command'
import { useOfferSearch, useRefreshOffers } from '@/hooks/use-campaign-creator'
import { useComboboxAria } from '@/hooks/use-combobox-aria'
import type { Offer } from '@/lib/api'
import { cn } from '@/lib/utils'

interface OfferComboboxProps {
  id?: string
  value: Offer | null
  onChange: (offer: Offer | null) => void
  invalid?: boolean
}

/**
 * Offer autocomplete: the user types an offer id or name straight into the field
 * and picks from matches listed below it. Search runs on the server over the
 * local offer catalog; matched text is emphasized in the results.
 */
export function OfferCombobox({ id, value, onChange, invalid }: OfferComboboxProps) {
  const [open, setOpen] = useState(false)
  // `text` is what the input shows; `query` is what we search for. They differ
  // once an offer is picked: the input shows its name, the search starts over.
  const [text, setText] = useState(value?.name ?? '')
  const [query, setQuery] = useState('')
  const { result: search, settled } = useOfferSearch(query, open)
  const refresh = useRefreshOffers()
  const offers = search.data ?? []
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  useComboboxAria(inputRef, listRef, open)

  // Follow selection changes made by the parent (e.g. reset after "Add offer").
  const [syncedValue, setSyncedValue] = useState(value)
  if (syncedValue !== value) {
    setSyncedValue(value)
    setText(value?.name ?? '')
    setQuery('')
  }

  // Results arrive asynchronously (debounce + request), after cmdk has already
  // highlighted the first item of the previous list. Keep the highlight
  // controlled and move it to the first result whenever new results arrive,
  // so Enter always picks the top match.
  const [highlight, setHighlight] = useState({ data: search.data, value: '' })
  let highlighted = highlight.value
  if (highlight.data !== search.data) {
    highlighted = offers.length > 0 ? String(offers[0].id) : ''
    setHighlight({ data: search.data, value: highlighted })
  }

  function pick(offer: Offer) {
    setSyncedValue(offer)
    setText(offer.name)
    setQuery('')
    setOpen(false)
    onChange(offer)
  }

  function type(next: string) {
    setText(next)
    setQuery(next)
    setOpen(true)
    if (value) {
      setSyncedValue(null)
      onChange(null)
    }
  }

  return (
    <div className="flex gap-2">
      <Command
        shouldFilter={false}
        value={highlighted}
        onValueChange={(next) => setHighlight({ data: search.data, value: next })}
        className="relative min-w-0 flex-1 overflow-visible bg-transparent p-0"
        onKeyDown={(event) => {
          if (event.key === 'Escape' && open) {
            event.preventDefault()
            setOpen(false)
          } else if (event.key === 'Enter' && !settled) {
            // The list still shows results for an older query; don't pick from it.
            // (cmdk skips its own Enter handling when the event is prevented.)
            event.preventDefault()
          } else if (event.key === 'ArrowDown' && !open) {
            setOpen(true)
          }
        }}
      >
        <input
          ref={inputRef}
          id={id}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-autocomplete="list"
          spellCheck={false}
          value={text}
          onChange={(event) => type(event.target.value)}
          onFocus={(event) => {
            event.currentTarget.select()
            setOpen(true)
          }}
          onBlur={() => {
            setOpen(false)
            // Leaving the field restores the picked offer's name.
            if (value) setText(value.name)
          }}
          placeholder="Type offer id or name…"
          autoComplete="off"
          aria-invalid={invalid}
          className={cn(
            'h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm transition-colors outline-none placeholder:text-muted-foreground',
            'focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50',
            'aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20',
            'dark:bg-input/30',
          )}
        />
        {open && (
          <div
            className="absolute inset-x-0 top-full z-50 mt-1 rounded-lg border bg-popover p-1 text-popover-foreground shadow-md"
            // Keep focus in the input while clicking a result.
            onMouseDown={(event) => event.preventDefault()}
          >
            <CommandList ref={listRef}>
              {search.isPending ? (
                <div className="py-6 text-center text-sm text-muted-foreground">Loading…</div>
              ) : search.isError ? (
                <div className="py-6 text-center text-sm text-destructive">
                  {search.error.message}
                </div>
              ) : (
                <CommandEmpty>No active offers found.</CommandEmpty>
              )}
              <CommandGroup>
                {offers.map((offer) => (
                  <CommandItem
                    key={offer.id}
                    value={String(offer.id)}
                    data-checked={value?.id === offer.id}
                    onSelect={() => pick(offer)}
                  >
                    <span className="w-12 shrink-0 font-mono text-xs text-muted-foreground">
                      <HighlightMatch text={String(offer.id)} query={query} />
                    </span>
                    <span className="truncate">
                      <HighlightMatch text={offer.name} query={query} />
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </div>
        )}
      </Command>
      <Button
        type="button"
        variant="outline"
        size="icon"
        title="Reload offers from Keitaro"
        aria-label="Reload offers from Keitaro"
        disabled={refresh.isPending}
        onClick={() => refresh.mutate()}
      >
        <RefreshCwIcon className={refresh.isPending ? 'animate-spin' : ''} />
      </Button>
    </div>
  )
}
