import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test } from 'vitest'

import { SettingField } from './SettingField'

test('shows an accessible overlay by hover, focus and click', async () => {
  render(
    <SettingField
      explanation="Nur Ergebnisse oberhalb dieses Vertrauenswerts werden übernommen."
      id="threshold"
      label="Genre-Schwelle"
    >
      <input id="threshold" />
    </SettingField>,
  )

  const help = screen.getByRole('button', { name: 'Erklärung zu Genre-Schwelle' })
  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  await userEvent.hover(help)
  expect(screen.getByRole('tooltip')).toHaveTextContent('Vertrauenswerts')
  expect(help).toHaveAttribute('aria-describedby', 'threshold-explanation')
  await userEvent.unhover(help)
  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()

  await userEvent.tab()
  expect(help).toHaveFocus()
  expect(screen.getByRole('tooltip')).toBeVisible()
  await userEvent.keyboard('{Escape}')
  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()

  await userEvent.click(help)
  expect(screen.getByRole('tooltip')).toHaveTextContent('Vertrauenswerts')
  expect(help).toHaveAttribute('aria-expanded', 'true')
})
