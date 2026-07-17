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
  const [openReason, setOpenReason] = useState<'hover' | 'focus' | 'click' | null>(null)
  const showExplanation = openReason !== null
  const explanationId = `${id}-explanation`

  return (
    <div className="setting-field">
      <span className="setting-field__heading">
        <label className="setting-field__label" htmlFor={id}>{label}</label>
        {explanation && (
          <span
            className="setting-field__help"
            onBlur={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget)) setOpenReason(null)
            }}
            onFocus={() => setOpenReason((current) => current === 'click' ? current : 'focus')}
            onMouseEnter={() => setOpenReason((current) => current ?? 'hover')}
            onMouseLeave={() => setOpenReason(null)}
          >
            <button
              aria-controls={explanationId}
              aria-describedby={showExplanation ? explanationId : undefined}
              aria-expanded={showExplanation}
              aria-label={`Erklärung zu ${label}`}
              className="setting-field__info"
              onClick={() => setOpenReason((current) => current === 'click' ? null : 'click')}
              onKeyDown={(event) => {
                if (event.key === 'Escape') setOpenReason(null)
              }}
              type="button"
            >
              <Info aria-hidden="true" size={13} />
            </button>
            {showExplanation && (
              <span className="setting-field__explanation" id={explanationId} role="tooltip">
                {explanation}
              </span>
            )}
          </span>
        )}
      </span>
      {children}
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
