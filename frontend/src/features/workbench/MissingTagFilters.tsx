import type { LibraryQuery } from './types'

type MissingTagFilterValue = Pick<LibraryQuery, 'missingGenre' | 'missingMood'>

interface MissingTagFiltersProps {
  value: MissingTagFilterValue
  onChange: (value: MissingTagFilterValue) => void
}

function filterStatus({ missingGenre, missingMood }: MissingTagFilterValue): string | null {
  if (missingGenre && missingMood) {
    return 'Titel mit vollständigen Genre- und Mood-Dateitags werden ausgeblendet.'
  }
  if (missingGenre) return 'Titel mit einem Genre-Dateitag werden ausgeblendet.'
  if (missingMood) return 'Titel mit einem Mood-Dateitag werden ausgeblendet.'
  return null
}

export function MissingTagFilters({ value, onChange }: MissingTagFiltersProps) {
  const status = filterStatus(value)

  return (
    <div className="quick-filters" aria-label="Fehlende Dateitags filtern">
      <div className="quick-filters__buttons">
        <button
          aria-pressed={value.missingGenre}
          className="quick-filter quick-filter--genre"
          onClick={() => onChange({ ...value, missingGenre: !value.missingGenre })}
          type="button"
        >
          Ohne Genre
        </button>
        <button
          aria-pressed={value.missingMood}
          className="quick-filter quick-filter--mood"
          onClick={() => onChange({ ...value, missingMood: !value.missingMood })}
          type="button"
        >
          Ohne Mood
        </button>
      </div>
      {status && <p className="quick-filters__status" role="status">{status}</p>}
    </div>
  )
}
