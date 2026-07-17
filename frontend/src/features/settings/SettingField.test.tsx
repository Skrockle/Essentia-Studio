import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test } from 'vitest'

import { SettingField } from './SettingField'

test('reveals an accessible explanation next to the setting name', async () => {
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
  await userEvent.click(help)
  expect(screen.getByRole('tooltip')).toHaveTextContent('Vertrauenswerts')
  expect(help).toHaveAttribute('aria-expanded', 'true')
})
