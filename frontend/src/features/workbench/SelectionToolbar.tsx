import { useState, type FormEvent } from 'react'
import { Plus, Tags } from 'lucide-react'

interface SelectionToolbarProps {
  selectedCount: number
  onBulkUpdate: (operation: string, value: string) => void
}

export function SelectionToolbar({ selectedCount, onBulkUpdate }: SelectionToolbarProps) {
  const [kind, setKind] = useState<'genre' | 'mood' | null>(null)
  const [value, setValue] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!kind || !value.trim()) return
    onBulkUpdate(`add_${kind}`, value.trim())
    setValue('')
    setKind(null)
  }

  return (
    <div className="selection-toolbar" data-visible={selectedCount > 0}>
      <span>
        <Tags aria-hidden="true" size={17} />
        <strong>{selectedCount} Titel ausgewählt</strong>
      </span>
      <button
        aria-label="Genre zu ausgewählten Titeln hinzufügen"
        disabled={!selectedCount}
        onClick={() => setKind('genre')}
        type="button"
      >
        <Plus aria-hidden="true" size={15} /> Genre
      </button>
      <button
        aria-label="Mood zu ausgewählten Titeln hinzufügen"
        disabled={!selectedCount}
        onClick={() => setKind('mood')}
        type="button"
      >
        <Plus aria-hidden="true" size={15} /> Mood
      </button>
      {kind && (
        <form onSubmit={submit}>
          <label htmlFor="bulk-tag">{kind === 'genre' ? 'Genre' : 'Mood'}</label>
          <input
            autoFocus
            id="bulk-tag"
            onChange={(event) => setValue(event.target.value)}
            value={value}
          />
        </form>
      )}
    </div>
  )
}
