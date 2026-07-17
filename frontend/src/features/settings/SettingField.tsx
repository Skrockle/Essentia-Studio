import type { ReactNode } from 'react'

import type { SettingSource } from '../../api/types'

interface SettingFieldProps {
  id: string
  label: string
  source?: SettingSource
  hint?: string
  children: ReactNode
}

export function SettingField({ id, label, source = 'default', hint, children }: SettingFieldProps) {
  return (
    <label className="setting-field" htmlFor={id}>
      <span className="setting-field__label">{label}</span>
      {children}
      {source === 'env' ? (
        <span className="setting-field__source" data-source="env">
          Durch Umgebungsvariable festgelegt
        </span>
      ) : (
        hint && <span className="setting-field__hint">{hint}</span>
      )}
    </label>
  )
}
