import { useId, useState, type FormEvent } from 'react'
import { Plus, X } from 'lucide-react'

interface TagEditorProps {
  kind: 'Genre' | 'Mood'
  values: string[]
  onChange: (values: string[]) => void
}

export function TagEditor({ kind, values, onChange }: TagEditorProps) {
  const inputId = useId()
  const [value, setValue] = useState('')

  function addValue(event: FormEvent) {
    event.preventDefault()
    const normalized = value.trim()
    if (!normalized) return
    if (!values.some((entry) => entry.toLocaleLowerCase() === normalized.toLocaleLowerCase())) {
      onChange([...values, normalized])
    }
    setValue('')
  }

  return (
    <div className="tag-editor" data-kind={kind.toLowerCase()}>
      <div className="tag-editor__chips">
        {values.map((tag) => (
          <span className="tag-chip" key={tag}>
            {tag}
            <button
              aria-label={`${kind} ${tag} entfernen`}
              onClick={() => onChange(values.filter((value) => value !== tag))}
              type="button"
            >
              <X aria-hidden="true" size={11} />
            </button>
          </span>
        ))}
      </div>
      <form className="tag-editor__form" onSubmit={addValue}>
        <label className="sr-only" htmlFor={inputId}>
          {kind} hinzufügen
        </label>
        <input
          id={inputId}
          maxLength={120}
          onChange={(event) => setValue(event.target.value)}
          placeholder={`${kind} ergänzen`}
          value={value}
        />
        <button aria-label={`${kind} hinzufügen`} type="submit">
          <Plus aria-hidden="true" size={13} />
        </button>
      </form>
    </div>
  )
}
