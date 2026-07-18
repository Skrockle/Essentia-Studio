import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import { JobProgress } from './JobProgress'

test('shows exact progress, successes, and failures', () => {
  render(
    <JobProgress
      event={{
        sequence: 2,
        job_id: 'analysis-1',
        kind: 'progress',
        payload: { total_items: 10, completed_items: 4, failed_items: 1 },
      }}
      job={{
        id: 'analysis-1',
        type: 'analysis',
        status: 'running',
        total_items: 10,
        completed_items: 0,
        failed_items: 0,
      }}
      label="Analyse"
    />,
  )

  expect(screen.getByRole('progressbar', { name: 'Analysefortschritt' })).toHaveAttribute(
    'aria-valuenow',
    '40',
  )
  expect(screen.getByText('4 von 10 verarbeitet')).toBeVisible()
  expect(screen.getByText('3 erfolgreich')).toBeVisible()
  expect(screen.getByText('1 fehlgeschlagen')).toBeVisible()
})
