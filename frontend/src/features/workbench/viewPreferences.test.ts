import { beforeEach, expect, test } from 'vitest'

import {
  DEFAULT_WORKBENCH_PREFERENCES,
  loadWorkbenchPreferences,
  saveWorkbenchPreferences,
  WORKBENCH_PREFERENCES_KEY,
} from './viewPreferences'

beforeEach(() => localStorage.clear())

test('uses safe defaults for missing or damaged preferences', () => {
  expect(loadWorkbenchPreferences()).toEqual(DEFAULT_WORKBENCH_PREFERENCES)
  localStorage.setItem(WORKBENCH_PREFERENCES_KEY, '{broken')
  expect(loadWorkbenchPreferences()).toEqual(DEFAULT_WORKBENCH_PREFERENCES)
})

test('persists only known filters and columns', () => {
  saveWorkbenchPreferences({
    ...DEFAULT_WORKBENCH_PREFERENCES,
    showWritten: true,
    formats: ['.flac', '.invalid'],
    libraryColumns: ['artist', 'title', 'file'],
  })

  expect(loadWorkbenchPreferences()).toMatchObject({
    showWritten: true,
    formats: ['.flac'],
    libraryColumns: ['artist', 'title', 'file'],
  })
})
