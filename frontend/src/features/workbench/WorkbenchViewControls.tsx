import { useState } from 'react'
import { Columns3, ListFilter, RotateCcw } from 'lucide-react'

import type { ProcessingState } from './types'
import {
  DEFAULT_WORKBENCH_PREFERENCES,
  LIBRARY_COLUMNS,
  type LibraryColumn,
  RESULT_COLUMNS,
  type ResultColumn,
  type WorkbenchViewPreferences,
} from './viewPreferences'

const stateLabels: Record<ProcessingState, string> = {
  new: 'Neu', current: 'Analysiert', changed: 'Verändert', written: 'Geschrieben', failed: 'Fehler',
}
const columnLabels: Record<LibraryColumn | ResultColumn, string> = {
  artist: 'Interpret', title: 'Titel', file: 'Datei', album: 'Album', format: 'Format',
  status: 'Status', genres: 'Genres', moods: 'Moods',
}

interface Props {
  availableFormats: string[]
  value: WorkbenchViewPreferences
  onChange: (value: WorkbenchViewPreferences) => void
}

function toggled<T extends string>(values: T[], value: T, enabled: boolean): T[] {
  return enabled ? [...new Set([...values, value])] : values.filter((item) => item !== value)
}

export function WorkbenchViewControls({ availableFormats, value, onChange }: Props) {
  const [openMenu, setOpenMenu] = useState<'filters' | 'columns' | null>(null)

  return (
    <section className="table-controls panel" aria-label="Tabellenansicht">
      <details
        onToggle={(event) => {
          if (event.currentTarget.open) setOpenMenu('filters')
          else setOpenMenu((current) => current === 'filters' ? null : current)
        }}
        open={openMenu === 'filters'}
      >
        <summary><ListFilter aria-hidden="true" size={16} /> Filter</summary>
        <div className="table-controls__menu">
          <strong>Status</strong>
          {(Object.keys(stateLabels) as ProcessingState[]).map((state) => (
            <label key={state}>
              <input
                checked={value.statuses.includes(state)}
                onChange={(event) => onChange({
                  ...value,
                  statuses: toggled(value.statuses, state, event.target.checked),
                })}
                type="checkbox"
              />
              {stateLabels[state]}
            </label>
          ))}
          <strong>Format</strong>
          {availableFormats.map((format) => (
            <label key={format}>
              <input
                checked={value.formats.length === 0 || value.formats.includes(format)}
                onChange={(event) => {
                  const current = value.formats.length === 0 ? availableFormats : value.formats
                  onChange({ ...value, formats: toggled(current, format, event.target.checked) })
                }}
                type="checkbox"
              />
              {format.slice(1).toUpperCase()}
            </label>
          ))}
          <label>
            <input
              aria-label="Vollständig geschriebene anzeigen"
              checked={value.showWritten}
              onChange={(event) => onChange({ ...value, showWritten: event.target.checked })}
              type="checkbox"
            />
            Vollständig geschriebene anzeigen
          </label>
        </div>
      </details>
      <details
        onToggle={(event) => {
          if (event.currentTarget.open) setOpenMenu('columns')
          else setOpenMenu((current) => current === 'columns' ? null : current)
        }}
        open={openMenu === 'columns'}
      >
        <summary><Columns3 aria-hidden="true" size={16} /> Spalten</summary>
        <div className="table-controls__menu table-controls__columns">
          <strong>Bibliothek</strong>
          {LIBRARY_COLUMNS.map((column) => (
            <label key={column}>
              <input
                aria-label={`Spalte ${columnLabels[column]} anzeigen`}
                checked={value.libraryColumns.includes(column)}
                onChange={(event) => onChange({
                  ...value,
                  libraryColumns: toggled(value.libraryColumns, column, event.target.checked),
                })}
                type="checkbox"
              />
              {columnLabels[column]}
            </label>
          ))}
          <strong>Ergebnisse</strong>
          {RESULT_COLUMNS.map((column) => (
            <label key={column}>
              <input
                aria-label={`Ergebnisspalte ${columnLabels[column]} anzeigen`}
                checked={value.resultColumns.includes(column)}
                onChange={(event) => onChange({
                  ...value,
                  resultColumns: toggled(value.resultColumns, column, event.target.checked),
                })}
                type="checkbox"
              />
              {columnLabels[column]}
            </label>
          ))}
        </div>
      </details>
      <button
        className="table-controls__reset"
        onClick={() => onChange(DEFAULT_WORKBENCH_PREFERENCES)}
        type="button"
      >
        <RotateCcw aria-hidden="true" size={15} /> Zurücksetzen
      </button>
    </section>
  )
}
