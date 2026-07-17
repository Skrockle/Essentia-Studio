import { X } from 'lucide-react'

import { TagCombobox } from './TagCombobox'

interface TagEditorProps {
  kind: 'Genre' | 'Mood'
  options: string[]
  values: string[]
  onChange: (values: string[]) => void
}

export function TagEditor({ kind, options, values, onChange }: TagEditorProps) {
  function addValue(value: string) {
    if (values.some((entry) => entry.toLocaleLowerCase() === value.toLocaleLowerCase())) return
    onChange([...values, value])
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
      <TagCombobox kind={kind} onAdd={addValue} options={options} selectedValues={values} />
    </div>
  )
}
