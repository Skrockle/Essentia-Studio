export const THEME_PREFERENCE_KEY = 'essentia-studio.theme.v1'

export type ThemePreference = 'system' | 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'

export function loadThemePreference(): ThemePreference {
  const stored = localStorage.getItem(THEME_PREFERENCE_KEY)
  return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'system'
}

export function saveThemePreference(preference: ThemePreference): void {
  localStorage.setItem(THEME_PREFERENCE_KEY, preference)
}

export function resolveTheme(
  preference: ThemePreference,
  systemPrefersDark: boolean,
): ResolvedTheme {
  return preference === 'system' ? (systemPrefersDark ? 'dark' : 'light') : preference
}
