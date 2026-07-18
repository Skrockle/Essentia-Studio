import { expect, test, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { JobStatusBar } from './JobStatusBar'
import type { JobRecord } from './types'

const job: JobRecord = {
  id: 'analysis-1',
  type: 'analysis',
  status: 'running',
  total_items: 10,
  completed_items: 4,
  failed_items: 0,
}

test('shows progress, remaining time, and an always available cancel action', async () => {
  const onCancel = vi.fn()
  render(
    <JobStatusBar
      etaSeconds={120}
      activeJob={job}
      onCancel={onCancel}
      onToggle={() => undefined}
      expanded={false}
      jobs={[job]}
    />,
  )

  expect(screen.getByText('Analyse')).toBeVisible()
  expect(screen.getByText('4 / 10')).toBeVisible()
  expect(screen.getByText('Restzeit ca. 2 min')).toBeVisible()
  await userEvent.click(screen.getByRole('button', { name: 'Job abbrechen' }))
  expect(onCancel).toHaveBeenCalledWith(job.id)
})
