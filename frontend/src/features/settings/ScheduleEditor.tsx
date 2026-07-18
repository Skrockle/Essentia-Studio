import type { AppSettings, AutomationStatus, SettingSource } from '../../api/types'
import { SettingField } from './SettingField'

type ScheduleKind = 'hourly' | 'daily' | 'weekly' | 'advanced'

interface ScheduleEditorProps {
  value: AppSettings['automation']
  sources: Record<string, SettingSource>
  status: AutomationStatus
  onChange: (value: AppSettings['automation']) => void
}

function scheduleKind(expression: string): ScheduleKind {
  const fields = expression.split(/\s+/)
  if (fields.length !== 5) return 'advanced'
  if (fields[1] === '*' && fields.slice(2).every((field) => field === '*')) return 'hourly'
  if (fields[2] === '*' && fields[3] === '*' && fields[4] === '*') return 'daily'
  if (fields[2] === '*' && fields[3] === '*' && fields[4] !== '*') return 'weekly'
  return 'advanced'
}

function timeFromCron(expression: string): string {
  const [minute = '0', hour = '3'] = expression.split(/\s+/)
  return `${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`
}

function withTime(expression: string, time: string): string {
  const [hour, minute] = time.split(':')
  const fields = expression.split(/\s+/)
  return `${Number(minute)} ${Number(hour)} ${fields[2] ?? '*'} ${fields[3] ?? '*'} ${fields[4] ?? '*'}`
}

function summary(value: AppSettings['automation']): string {
  const kind = scheduleKind(value.schedule)
  if (kind === 'hourly') return 'Jede Stunde zur Minute 0'
  if (kind === 'daily') return `Täglich um ${timeFromCron(value.schedule)} Uhr`
  if (kind === 'weekly') {
    const weekday = value.schedule.split(/\s+/)[4]
    const names: Record<string, string> = {
      '0': 'Sonntag',
      '1': 'Montag',
      '2': 'Dienstag',
      '3': 'Mittwoch',
      '4': 'Donnerstag',
      '5': 'Freitag',
      '6': 'Samstag',
    }
    return `${names[weekday] ?? 'Wöchentlich'} um ${timeFromCron(value.schedule)} Uhr`
  }
  return `Erweiterter Zeitplan: ${value.schedule}`
}

export function ScheduleEditor({ value, sources, status, onChange }: ScheduleEditorProps) {
  const kind = scheduleKind(value.schedule)
  const scheduleLocked = sources['automation.schedule'] === 'env'
  const timezoneLocked = sources['automation.timezone'] === 'env'
  const fields = value.schedule.split(/\s+/)

  function changeKind(next: ScheduleKind) {
    const schedules: Record<Exclude<ScheduleKind, 'advanced'>, string> = {
      hourly: '0 * * * *',
      daily: '0 3 * * *',
      weekly: '0 3 * * 1',
    }
    if (next !== 'advanced') onChange({ ...value, schedule: schedules[next] })
  }

  return (
    <section className="schedule-editor" aria-label="Zeitplan">
      <div className="schedule-editor__heading">
        <div>
          <span className="signal-dot" aria-hidden="true" />
          <strong>Zeitplan</strong>
        </div>
        <span>{summary(value)}</span>
      </div>
      <div className="form-grid schedule-editor__grid">
        <SettingField id="schedule-kind" label="Häufigkeit" source={sources['automation.schedule']}>
          <select
            id="schedule-kind"
            value={kind}
            disabled={scheduleLocked}
            onChange={(event) => changeKind(event.target.value as ScheduleKind)}
          >
            <option value="hourly">Stündlich</option>
            <option value="daily">Täglich</option>
            <option value="weekly">Wöchentlich</option>
            <option value="advanced">Erweitert (Cron)</option>
          </select>
        </SettingField>
        {kind !== 'hourly' && kind !== 'advanced' && (
          <SettingField id="schedule-time" label="Uhrzeit" source={sources['automation.schedule']}>
            <input
              id="schedule-time"
              type="time"
              value={timeFromCron(value.schedule)}
              disabled={scheduleLocked}
              onChange={(event) => onChange({ ...value, schedule: withTime(value.schedule, event.target.value) })}
            />
          </SettingField>
        )}
        {kind === 'weekly' && (
          <SettingField id="schedule-weekday" label="Wochentag" source={sources['automation.schedule']}>
            <select
              id="schedule-weekday"
              value={fields[4]}
              disabled={scheduleLocked}
              onChange={(event) =>
                onChange({ ...value, schedule: `${fields.slice(0, 4).join(' ')} ${event.target.value}` })
              }
            >
              <option value="1">Montag</option>
              <option value="2">Dienstag</option>
              <option value="3">Mittwoch</option>
              <option value="4">Donnerstag</option>
              <option value="5">Freitag</option>
              <option value="6">Samstag</option>
              <option value="0">Sonntag</option>
            </select>
          </SettingField>
        )}
        {kind === 'advanced' && (
          <SettingField
            id="schedule-cron"
            label="Cron-Ausdruck"
            source={sources['automation.schedule']}
            hint="Fünf Felder: Minute Stunde Tag Monat Wochentag"
          >
            <input
              id="schedule-cron"
              value={value.schedule}
              disabled={scheduleLocked}
              onChange={(event) => onChange({ ...value, schedule: event.target.value })}
            />
          </SettingField>
        )}
        <SettingField id="schedule-timezone" label="Zeitzone" source={sources['automation.timezone']}>
          <select
            id="schedule-timezone"
            value={value.timezone}
            disabled={timezoneLocked}
            onChange={(event) => onChange({ ...value, timezone: event.target.value })}
          >
            <option value="Europe/Berlin">Europe/Berlin</option>
            <option value="UTC">UTC</option>
          </select>
        </SettingField>
      </div>
      {status.next_runs.length > 0 && (
        <div className="next-runs">
          <span>Nächste Läufe</span>
          {status.next_runs.map((run) => (
            <time key={run} dateTime={run}>
              {new Intl.DateTimeFormat('de-DE', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(run))}
            </time>
          ))}
        </div>
      )}
    </section>
  )
}
