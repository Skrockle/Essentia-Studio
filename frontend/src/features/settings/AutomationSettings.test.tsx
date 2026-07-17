import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'

import type { AppSettings, AutomationStatus } from '../../api/types'
import { AutomationSettings } from './AutomationSettings'

const value: AppSettings['automation'] = {
  enabled: true,
  watcher: true,
  schedule: '0 * * * *',
  timezone: 'Europe/Berlin',
  mode: 'analyze',
  quiet_seconds: 30,
}

const status: AutomationStatus = {
  enabled: true,
  trigger_mode: 'watcher',
  watcher_health: 'ready',
  next_runs: [],
  last_run: null,
  last_error: null,
}

test('turning watcher off opens understandable schedule settings', async () => {
  const onChange = vi.fn()
  function Harness() {
    const [current, setCurrent] = useState(value)
    return (
      <AutomationSettings
        value={current}
        sources={{}}
        status={status}
        writeConfirmed={false}
        onWriteConfirmedChange={vi.fn()}
        onChange={(next) => {
          onChange(next)
          setCurrent(next)
        }}
      />
    )
  }
  render(<Harness />)

  await userEvent.click(screen.getByRole('checkbox', { name: 'Dateiüberwachung' }))

  expect(onChange).toHaveBeenCalledWith({ ...value, watcher: false })
  expect(screen.getByRole('region', { name: 'Zeitplan' })).toBeVisible()
  expect(screen.getByLabelText('Häufigkeit')).toBeVisible()
})
