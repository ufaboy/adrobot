import { render, screen } from '@testing-library/react'
import { PlusIcon } from 'lucide-react'
import { describe, expect, it } from 'vitest'

import { Button } from '@/components/ui/button'

describe('Button loading state', () => {
  it('is disabled, busy and shows a spinner while loading', () => {
    render(
      <Button loading>
        <PlusIcon />
        Save
      </Button>,
    )

    const button = screen.getByRole('button', { name: 'Save' })
    expect(button).toBeDisabled()
    expect(button).toHaveAttribute('aria-busy', 'true')
    expect(button.querySelector('[data-spinner]')).not.toBeNull()
  })

  it('looks normal when not loading', () => {
    render(<Button>Save</Button>)

    const button = screen.getByRole('button', { name: 'Save' })
    expect(button).toBeEnabled()
    expect(button).not.toHaveAttribute('aria-busy')
    expect(button.querySelector('[data-spinner]')).toBeNull()
  })
})
