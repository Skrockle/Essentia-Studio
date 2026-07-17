import { beforeEach, expect, test } from 'vitest'

import {
  loadThemePreference,
  resolveTheme,
  saveThemePreference,
  THEME_PREFERENCE_KEY,
} from './theme'

beforeEach(() => localStorage.clear())

test('loads only supported persistent theme preferences', () => {
  expect(loadThemePreference()).toBe('system')
  localStorage.setItem(THEME_PREFERENCE_KEY, 'dark')
  expect(loadThemePreference()).toBe('dark')
  localStorage.setItem(THEME_PREFERENCE_KEY, 'unknown')
  expect(loadThemePreference()).toBe('system')
})

test('resolves system preference and persists explicit choices', () => {
  expect(resolveTheme('system', true)).toBe('dark')
  expect(resolveTheme('system', false)).toBe('light')
  expect(resolveTheme('light', true)).toBe('light')

  saveThemePreference('dark')
  expect(localStorage.getItem(THEME_PREFERENCE_KEY)).toBe('dark')
})
