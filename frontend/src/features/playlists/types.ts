export interface CatalogItem {
  key: string
  label: string
}

export interface PlaylistField extends CatalogItem {
  type: 'string' | 'number' | 'boolean' | 'date' | 'playlist'
  category: string
}

export interface PlaylistPreset {
  label: string
  slug: string
  category: string
  definition: Record<string, unknown>
}

export interface ThisIsMethod {
  id: string
  label: string
}

export interface PlaylistCatalog {
  fields: PlaylistField[]
  operators: Record<string, CatalogItem[]>
  sort_options: CatalogItem[]
  presets: PlaylistPreset[]
  this_is_methods: ThisIsMethod[]
}

export interface PlaylistFile {
  name: string
  definition: Record<string, unknown> | null
  fingerprint: string
  status: string
  error: string | null
}
