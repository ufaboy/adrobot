import { type RefObject, useEffect } from 'react'

/**
 * Wires combobox ARIA attributes from a plain `<input>` to a cmdk list.
 *
 * cmdk's own `Command.Input` overwrites `id` (breaking `<label htmlFor>`) and
 * always reports `aria-expanded="true"`, so our pickers use a plain input inside
 * `Command` (cmdk still handles arrow keys and Enter on the root). cmdk generates
 * the list and item ids itself, so they are read back from the DOM after render.
 */
export function useComboboxAria(
  input: RefObject<HTMLInputElement | null>,
  list: RefObject<HTMLElement | null>,
  open: boolean,
) {
  useEffect(() => {
    const el = input.current
    if (!el) return
    const listId = open ? list.current?.id : undefined
    const activeId = open
      ? list.current?.querySelector('[cmdk-item][data-selected="true"]')?.id
      : undefined
    setOrRemove(el, 'aria-controls', listId)
    setOrRemove(el, 'aria-activedescendant', activeId)
  })
}

function setOrRemove(el: HTMLElement, name: string, value: string | undefined) {
  if (value) el.setAttribute(name, value)
  else el.removeAttribute(name)
}
