import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'

import { MissingTagFilters } from './MissingTagFilters'

test('toggles missing genre and mood independently', async () => {
  const onChange = vi.fn()
  render(<MissingTagFilters value={{ missingGenre: false, missingMood: false }} onChange={onChange} />)

  await userEvent.click(screen.getByRole('button', { name: 'Ohne Genre' }))

  expect(onChange).toHaveBeenCalledWith({ missingGenre: true, missingMood: false })
})

test('exposes the active missing mood filter as pressed', () => {
  render(<MissingTagFilters value={{ missingGenre: false, missingMood: true }} onChange={vi.fn()} />)

  expect(screen.getByRole('button', { name: 'Ohne Mood' })).toHaveAttribute('aria-pressed', 'true')
})
