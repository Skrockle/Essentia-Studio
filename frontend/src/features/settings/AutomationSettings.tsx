import { AlertTriangle, Radio, TimerReset } from 'lucide-react'

import type { AppSettings, AutomationStatus, SettingSource } from '../../api/types'
import { ScheduleEditor } from './ScheduleEditor'
import { SettingField } from './SettingField'

interface AutomationSettingsProps {
  value: AppSettings['automation']
  sources: Record<string, SettingSource>
  status: AutomationStatus
  writeConfirmed: boolean
  onWriteConfirmedChange: (confirmed: boolean) => void
  onChange: (value: AppSettings['automation']) => void
}

// The branches mirror independently visible form sections, not algorithmic state.
// eslint-disable-next-line complexity
export function AutomationSettings({
  value,
  sources,
  status,
  writeConfirmed,
  onWriteConfirmedChange,
  onChange,
}: AutomationSettingsProps) {
  const failedWatcher = status.watcher_health === 'failed'
  const showSchedule = value.enabled && (!value.watcher || failedWatcher)

  return (
    <section className="panel settings-section automation-panel" aria-labelledby="automation-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Neue & geänderte Titel</p>
          <h2 id="automation-heading">Automatik</h2>
        </div>
        <div className="automation-state" data-state={status.trigger_mode}>
          <span aria-hidden="true" />
          {value.enabled ? 'Aktiv' : 'Aus'}
        </div>
      </div>

      <div className="automation-signal-rail" aria-label="Automationsstatus">
        <Radio aria-hidden="true" size={19} />
        <div>
          <strong>{value.watcher ? 'Dateisignal' : 'Zeitplan'}</strong>
          <span>
            {failedWatcher
              ? 'Dateiüberwachung nicht verfügbar – der Zeitplan übernimmt.'
              : value.enabled
                ? value.watcher
                  ? 'Wartet auf stabile neue oder geänderte Audiodateien.'
                  : 'Prüft die Mediathek zum eingestellten Zeitpunkt.'
                : 'Es werden keine Titel automatisch verarbeitet.'}
          </span>
        </div>
        <span className="automation-signal-rail__mode">{status.trigger_mode.replace('_', ' ')}</span>
      </div>

      {failedWatcher && (
        <p className="inline-warning">
          <AlertTriangle aria-hidden="true" size={17} />
          {status.last_error ?? 'Der Mount liefert keine zuverlässigen Datei-Ereignisse.'}
        </p>
      )}

      <div className="automation-controls">
        <label className="switch-row">
          <span>
            <strong>Automatik aktivieren</strong>
            <small>Verarbeitet nur neue oder seit der letzten Analyse geänderte Titel.</small>
          </span>
          <input
            type="checkbox"
            checked={value.enabled}
            disabled={sources['automation.enabled'] === 'env'}
            onChange={(event) => onChange({ ...value, enabled: event.target.checked })}
          />
        </label>

        {value.enabled && (
          <>
            <label className="switch-row">
              <span>
                <strong>Dateiüberwachung</strong>
                <small>Bei Aus wird automatisch der verständliche Zeitplan eingeblendet.</small>
              </span>
              <input
                aria-label="Dateiüberwachung"
                type="checkbox"
                checked={value.watcher}
                disabled={sources['automation.watcher'] === 'env'}
                onChange={(event) => onChange({ ...value, watcher: event.target.checked })}
              />
            </label>
            {value.watcher && !failedWatcher && (
              <SettingField
                id="quiet-seconds"
                label="Ruhezeit vor der Analyse"
                source={sources['automation.quiet_seconds']}
                hint="Die Dateigröße und Änderungszeit müssen so lange stabil bleiben."
              >
                <span className="input-with-unit">
                  <input
                    id="quiet-seconds"
                    min="5"
                    max="3600"
                    type="number"
                    value={value.quiet_seconds}
                    disabled={sources['automation.quiet_seconds'] === 'env'}
                    onChange={(event) => onChange({ ...value, quiet_seconds: Number(event.target.value) })}
                  />
                  <span>Sek.</span>
                </span>
              </SettingField>
            )}
          </>
        )}
      </div>

      {showSchedule && (
        <ScheduleEditor value={value} sources={sources} status={status} onChange={onChange} />
      )}

      {value.enabled && (
        <div className="automatic-write">
          <label className="switch-row switch-row--danger">
            <span>
              <strong>Analysen automatisch in Dateien schreiben</strong>
              <small>Ohne diese Option bleiben Ergebnisse als prüfbare Vorschau liegen.</small>
            </span>
            <input
              type="checkbox"
              checked={value.mode === 'analyze_and_write'}
              disabled={sources['automation.mode'] === 'env'}
              onChange={(event) => {
                onWriteConfirmedChange(false)
                onChange({ ...value, mode: event.target.checked ? 'analyze_and_write' : 'analyze' })
              }}
            />
          </label>
          {value.mode === 'analyze_and_write' && sources['automation.mode'] !== 'env' && (
            <label className="write-confirmation">
              <input
                type="checkbox"
                checked={writeConfirmed}
                onChange={(event) => onWriteConfirmedChange(event.target.checked)}
              />
              <span>
                <TimerReset aria-hidden="true" size={17} />
                Ich bestätige: erfolgreiche Entwürfe werden direkt geschrieben; Undo bleibt verfügbar.
              </span>
            </label>
          )}
        </div>
      )}
    </section>
  )
}
