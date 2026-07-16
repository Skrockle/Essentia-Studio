export type RuleNode = ConditionNode | GroupNode

export interface ConditionNode {
  id: string
  kind: 'condition'
  field: string
  operator: string
  value: string | number | boolean
}

export interface GroupNode {
  id: string
  kind: 'group'
  mode: 'all' | 'any'
  children: RuleNode[]
}

let nextId = 0

export function condition(field = 'title', operator = 'is'): ConditionNode {
  return { id: `condition-${nextId++}`, kind: 'condition', field, operator, value: '' }
}

export function group(mode: 'all' | 'any' = 'all', children = [condition()]): GroupNode {
  return { id: `group-${nextId++}`, kind: 'group', mode, children }
}

export function updateNode(root: GroupNode, id: string, update: (node: RuleNode) => RuleNode): GroupNode {
  return mapGroup(root, (node) => (node.id === id ? update(node) : node))
}

export function addNode(root: GroupNode, parentId: string, node: RuleNode): GroupNode {
  return mapGroup(root, (current) => {
    if (current.id !== parentId || current.kind !== 'group') return current
    return { ...current, children: [...current.children, node] }
  })
}

export function removeNode(root: GroupNode, id: string): GroupNode {
  return {
    ...root,
    children: root.children
      .filter((node) => node.id !== id)
      .map((node) => (node.kind === 'group' ? removeNode(node, id) : node)),
  }
}

export function serializeGroup(root: GroupNode): Record<string, unknown> {
  return {
    [root.mode]: root.children.map((node) => {
      if (node.kind === 'group') return serializeGroup(node)
      return { [node.operator]: { [node.field]: node.value } }
    }),
  }
}

function mapGroup(root: GroupNode, map: (node: RuleNode) => RuleNode): GroupNode {
  const mapped = map(root) as GroupNode
  return {
    ...mapped,
    children: mapped.children.map((node) =>
      node.kind === 'group' ? mapGroup(node, map) : map(node),
    ),
  }
}
