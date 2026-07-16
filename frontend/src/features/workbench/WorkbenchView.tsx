import { useMemo, useState } from 'react'
import { AudioWaveform, Search, Sparkles } from 'lucide-react'

import { ResultTable } from './ResultTable'
import { SelectionToolbar } from './SelectionToolbar'
import { useResults } from './useResults'

export function WorkbenchView() {
  const [search, setSearch] = useState('')
  const query = useMemo(() => ({ search }), [search])
  const { page, error, selectAll, selectRow, saveDraft, bulkUpdate } = useResults(query)
  const allSelected = page.total > 0 && page.selected_count === page.total

  return (
    <div className="view-stack">
      <header className="workbench-hero">
        <div>
          <p className="eyebrow">Mediathek-Analyse</p>
          <h1>Aus Klang wird Ordnung.</h1>
          <p>
            Genres und Moods prüfen, manuell verfeinern und erst nach einer Vorschau in die
            Musikdateien schreiben.
          </p>
        </div>
        <div className="signal-wave" aria-hidden="true">
          {[14, 28, 19, 42, 31, 55, 24, 47, 63, 34, 51, 25, 39, 18, 31, 13].map(
            (height, index) => <span key={index} style={{ height }} />,
          )}
        </div>
      </header>

      <section className="workbench-controls panel">
        <label className="search-field">
          <Search aria-hidden="true" size={17} />
          <span className="sr-only">Ergebnisse filtern</span>
          <input
            aria-label="Ergebnisse filtern"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Titel oder Pfad filtern …"
            type="search"
            value={search}
          />
        </label>
        <div className="result-summary">
          <Sparkles aria-hidden="true" size={17} />
          <strong>{page.total}</strong> analysierte Titel
        </div>
      </section>

      <SelectionToolbar selectedCount={page.selected_count} onBulkUpdate={bulkUpdate} />

      {error && <p className="notice notice--error">{error}</p>}
      {!error && page.items.length === 0 ? (
        <section className="panel workbench-empty">
          <div className="empty-icon">
            <AudioWaveform aria-hidden="true" size={30} />
          </div>
          <div>
            <p className="eyebrow">Noch keine Vorschläge</p>
            <h2>Scanne und analysiere deine Mediathek</h2>
            <p>Die Ergebnisse erscheinen hier zur Prüfung, ohne deine Dateien zu verändern.</p>
          </div>
        </section>
      ) : (
        <ResultTable
          allSelected={allSelected}
          onSaveDraft={saveDraft}
          onSelectAll={selectAll}
          onSelectRow={selectRow}
          rows={page.items}
        />
      )}
    </div>
  )
}
