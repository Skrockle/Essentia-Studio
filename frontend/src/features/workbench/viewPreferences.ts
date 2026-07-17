import type { ProcessingState } from './types'

export const WORKBENCH_PREFERENCES_KEY = 'essentia-studio.workbench.v1'

export const AUDIO_FORMATS = [
  '.aac', '.aif', '.aiff', '.ape', '.dsf', '.flac', '.m4a', '.m4b', '.mp+',
  '.mp3', '.mp4', '.mpc', '.oga', '.ogg', '.opus', '.wav', '.wma', '.wv',
] as const

export const PROCESSING_STATES: ProcessingState[] = [
  'new', 'current', 'changed', 'written', 'failed',
]

export const LIBRARY_COLUMNS = ['artist', 'title', 'file', 'album', 'format', 'status'] as const
export const RESULT_COLUMNS = ['artist', 'title', 'file', 'genres', 'moods', 'status'] as const

export type LibraryColumn = typeof LIBRARY_COLUMNS[number]
export type ResultColumn = typeof RESULT_COLUMNS[number]

export interface WorkbenchViewPreferences {
  statuses: ProcessingState[]
  formats: string[]
  showWritten: boolean
  libraryColumns: LibraryColumn[]
  resultColumns: ResultColumn[]
}

export const DEFAULT_WORKBENCH_PREFERENCES: WorkbenchViewPreferences = {
  statuses: [...PROCESSING_STATES],
  formats: [],
  showWritten: false,
  libraryColumns: [...LIBRARY_COLUMNS],
  resultColumns: [...RESULT_COLUMNS],
}

function knownValues<T extends string>(value: unknown, known: readonly T[]): T[] {
  if (!Array.isArray(value)) return [...known]
  return value.filter((item): item is T => typeof item === 'string' && known.includes(item as T))
}

export function loadWorkbenchPreferences(): WorkbenchViewPreferences {
  try {
    const stored = JSON.parse(localStorage.getItem(WORKBENCH_PREFERENCES_KEY) ?? 'null')
    if (!stored || typeof stored !== 'object') return DEFAULT_WORKBENCH_PREFERENCES
    return {
      statuses: knownValues(stored.statuses, PROCESSING_STATES),
      formats: knownValues(stored.formats, AUDIO_FORMATS),
      showWritten: stored.showWritten === true,
      libraryColumns: knownValues(stored.libraryColumns, LIBRARY_COLUMNS),
      resultColumns: knownValues(stored.resultColumns, RESULT_COLUMNS),
    }
  } catch {
    return DEFAULT_WORKBENCH_PREFERENCES
  }
}

export function saveWorkbenchPreferences(value: WorkbenchViewPreferences): void {
  localStorage.setItem(WORKBENCH_PREFERENCES_KEY, JSON.stringify({
    statuses: knownValues(value.statuses, PROCESSING_STATES),
    formats: knownValues(value.formats, AUDIO_FORMATS),
    showWritten: value.showWritten === true,
    libraryColumns: knownValues(value.libraryColumns, LIBRARY_COLUMNS),
    resultColumns: knownValues(value.resultColumns, RESULT_COLUMNS),
  }))
}
