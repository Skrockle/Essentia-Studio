import { Plus, Trash2 } from 'lucide-react'

import type { PlaylistCatalog, PlaylistField } from './types'
import { addNode, condition, group, removeNode, type GroupNode, type RuleNode, updateNode } from './rules'

interface Props {
  catalog: PlaylistCatalog
  root: GroupNode
  node: GroupNode
  depth?: number
  onChange: (root: GroupNode) => void
}

export function RuleGroup({ catalog, root, node, depth = 0, onChange }: Props) {
  function updateCondition(id: string, update: Partial<RuleNode>) {
    onChange(updateNode(root, id, (current) => ({ ...current, ...update }) as RuleNode))
  }

  return (
    <fieldset className="rule-group" data-depth={depth}>
      <legend>{node.mode === 'all' ? 'UND – alle Regeln' : 'ODER – mindestens eine Regel'}</legend>
      {node.children.map((child) => child.kind === 'group' ? (
        <div className="nested-rule" key={child.id}>
          <RuleGroup catalog={catalog} depth={depth + 1} node={child} onChange={onChange} root={root} />
          <button aria-label="Gruppe entfernen" onClick={() => onChange(removeNode(root, child.id))} type="button"><Trash2 size={14} /></button>
        </div>
      ) : (
        <ConditionEditor
          catalog={catalog}
          key={child.id}
          node={child}
          onRemove={() => onChange(removeNode(root, child.id))}
          onUpdate={(update) => updateCondition(child.id, update)}
        />
      ))}
      <div className="rule-actions">
        <button onClick={() => onChange(addNode(root, node.id, condition()))} type="button"><Plus size={14} /> Regel hinzufügen</button>
        <button disabled={depth >= 11} onClick={() => onChange(addNode(root, node.id, group('any')))} type="button"><Plus size={14} /> ODER-Gruppe hinzufügen</button>
      </div>
    </fieldset>
  )
}

interface ConditionProps {
  catalog: PlaylistCatalog
  node: Extract<RuleNode, { kind: 'condition' }>
  onUpdate: (update: Partial<RuleNode>) => void
  onRemove: () => void
}

function ConditionEditor({ catalog, node, onUpdate, onRemove }: ConditionProps) {
  const field = catalog.fields.find((item) => item.key === node.field) ?? catalog.fields[0]
  const operators = catalog.operators[field.type]

  function selectField(nextKey: string) {
    const nextField = catalog.fields.find((item) => item.key === nextKey) as PlaylistField
    onUpdate({ field: nextKey, operator: catalog.operators[nextField.type][0].key, value: initialValue(nextField) })
  }

  return (
    <div className="condition-row">
      <label>Feld<select onChange={(event) => selectField(event.target.value)} value={node.field}>{catalog.fields.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
      <label>Operator<select onChange={(event) => onUpdate({ operator: event.target.value })} value={node.operator}>{operators.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
      <ValueInput field={field} node={node} onUpdate={onUpdate} />
      <button aria-label="Regel entfernen" onClick={onRemove} type="button"><Trash2 size={14} /></button>
    </div>
  )
}

function ValueInput({ field, node, onUpdate }: { field: PlaylistField; node: Extract<RuleNode, { kind: 'condition' }>; onUpdate: (update: Partial<RuleNode>) => void }) {
  if (field.type === 'boolean') {
    return <label>Wert<select aria-label="Wert" onChange={(event) => onUpdate({ value: event.target.value === 'true' })} value={String(node.value)}><option value="true">Ja</option><option value="false">Nein</option></select></label>
  }
  const type = field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text'
  return <label>Wert<input aria-label="Wert" onChange={(event) => onUpdate({ value: type === 'number' ? Number(event.target.value) : event.target.value })} type={type} value={String(node.value)} /></label>
}

function initialValue(field: PlaylistField): string | number | boolean {
  if (field.type === 'boolean') return true
  if (field.type === 'number') return 0
  return ''
}
