import { expect, test } from '@playwright/test'

test('edits recommended analysis thresholds as percentages', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Einstellungen' }).click()

  const genreThreshold = page.getByLabel('Genre-Schwelle', { exact: true })
  const moodThreshold = page.getByLabel('Mood-Schwelle', { exact: true })
  await expect(genreThreshold).toHaveValue('25')
  await expect(moodThreshold).toHaveValue('10')

  const help = page.getByRole('button', { name: 'Erklärung zu Genre-Schwelle' })
  await help.hover()
  const tooltip = page.getByRole('tooltip')
  await expect(tooltip).toBeVisible()
  await expect(tooltip).toHaveCSS('position', 'absolute')

  await genreThreshold.fill('30')
  await moodThreshold.fill('12')
  await page.getByRole('button', { name: 'Änderungen speichern' }).click()
  await expect(page.getByText('Änderungen gespeichert.')).toBeVisible()

  const stored = await page.evaluate(async () => {
    const response = await fetch('/api/settings')
    return response.json()
  })
  expect(stored.values.analysis.genre_threshold).toBe(0.3)
  expect(stored.values.analysis.mood_threshold).toBe(0.12)
})
