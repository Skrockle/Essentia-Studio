import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'

import { UncertainGenreSuggestion } from './UncertainGenreSuggestion'

test('presents a rejected hierarchy separately and accepts its split genres', async () => {
  const onAccept = vi.fn()

  render(
    <UncertainGenreSuggestion
      onAccept={onAccept}
      prediction={{
        label: 'Rock---Alternative Rock',
        confidence: 0.116,
        accepted: false,
      }}
    />,
  )

  expect(screen.getByText('Unter der Schwelle')).toBeVisible()
  expect(screen.getByText(/11,6/)).toBeVisible()
  expect(screen.getByText('Rock')).toBeVisible()
  expect(screen.getByText('Alternative Rock')).toBeVisible()

  await userEvent.click(screen.getByRole('button', { name: 'Unsichere Genres übernehmen' }))

  expect(onAccept).toHaveBeenCalledWith(['Rock', 'Alternative Rock'])
})
