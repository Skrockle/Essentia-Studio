import { expect, test } from '@playwright/test'

test('persists theme and configurable library columns', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Bibliothek scannen' }).click()
  await expect(page.getByText('Scan abgeschlossen')).toBeVisible()

  await page.getByLabel('Farbschema').selectOption('dark')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')

  await page.getByText('Spalten', { exact: true }).click()
  await page.getByRole('checkbox', { name: 'Spalte Datei anzeigen', exact: true }).uncheck()
  const library = page.getByRole('region', { name: 'Titel für die Analyse auswählen' })
  await expect(library.getByRole('columnheader', { name: 'Datei' })).toHaveCount(0)

  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.getByLabel('Farbschema')).toHaveValue('dark')
  await expect(library.getByRole('columnheader', { name: 'Datei' })).toHaveCount(0)

  await page.getByRole('button', { name: 'Einstellungen' }).click()
  const saveButton = page.getByRole('button', { name: 'Änderungen speichern' })
  await expect(saveButton).toBeVisible()
  const colors = await saveButton.evaluate((button) => {
    const style = getComputedStyle(button)
    return { background: style.backgroundColor, foreground: style.color }
  })
  expect(colors.foreground).not.toBe(colors.background)
})
