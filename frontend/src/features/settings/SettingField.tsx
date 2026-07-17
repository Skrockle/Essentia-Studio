import { useState, type ReactNode } from 'react'
import { Info } from 'lucide-react'

import type { SettingSource } from '../../api/types'

interface SettingFieldProps {
  id: string
  label: string
  source?: SettingSource
  hint?: string
  explanation?: string
  children: ReactNode
}

export function SettingField({
  id,
  label,
  source = 'default',
  hint,
  explanation,
  children,
}: SettingFieldProps) {
  const [showExplanation, setShowExplanation] = useState(false)
  const explanationId = `${id}-explanation`

  return (
    <div className="setting-field">
      <span className="setting-field__heading">
        <label className="setting-field__label" htmlFor={id}>{label}</label>
        {explanation && (
          <button
            aria-controls={explanationId}
            aria-expanded={showExplanation}
            aria-label={`Erklärung zu ${label}`}
            className="setting-field__info"
            onClick={() => setShowExplanation((current) => !current)}
            type="button"
          >
            <Info aria-hidden="true" size={13} />
          </button>
        )}
      </span>
      {children}
      {explanation && showExplanation && (
        <span className="setting-field__explanation" id={explanationId} role="tooltip">
          {explanation}
        </span>
      )}
      {source === 'env' ? (
        <span className="setting-field__source" data-source="env">
          Durch Umgebungsvariable festgelegt
        </span>
      ) : (
        hint && <span className="setting-field__hint">{hint}</span>
      )}
    </div>
  )
}
