import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { NamedItem } from '@/lib/api'

interface IdSelectProps {
  id?: string
  items: NamedItem[]
  value: number | undefined
  onChange: (id: number) => void
  placeholder: string
  invalid?: boolean
}

/** Select over Keitaro reference items (domains, groups, traffic sources). */
export function IdSelect({ id, items, value, onChange, placeholder, invalid }: IdSelectProps) {
  return (
    <Select
      items={items.map((item) => ({ value: item.id, label: item.name }))}
      value={value ?? null}
      onValueChange={(next) => {
        if (typeof next === 'number') onChange(next)
      }}
    >
      <SelectTrigger id={id} className="w-full" aria-invalid={invalid}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {items.map((item) => (
          <SelectItem key={item.id} value={item.id}>
            {item.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
