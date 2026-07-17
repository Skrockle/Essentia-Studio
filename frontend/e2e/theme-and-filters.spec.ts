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

test('uses dark surfaces throughout the workbench', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Bibliothek scannen' }).click()
  await expect(page.getByText('Scan abgeschlossen')).toBeVisible()

  if (await page.locator('.result-table th').count() === 0) {
    await page.getByRole('checkbox', { name: 'Alle gescannten Titel analysieren' }).check()
    await page.getByRole('button', { name: '1 Titel analysieren' }).click()
    await expect(page.getByText('Analyse abgeschlossen')).toBeVisible()
  }

  await page.getByLabel('Farbschema').selectOption('dark')
  await page.waitForTimeout(180)
  const surfaces = await page.evaluate(() => {
    const selectors = {
      navigation: '.app-nav',
      libraryHeader: '.library-table th',
      selectionToolbar: '.selection-toolbar',
      resultHeader: '.result-table th',
      tagInput: '.tag-editor input',
    }
    return Object.fromEntries(Object.entries(selectors).map(([name, selector]) => {
      const element = document.querySelector(selector)
      return [name, element ? getComputedStyle(element).backgroundColor : null]
    }))
  })

  for (const [name, color] of Object.entries(surfaces)) {
    expect(color, `${name} should exist`).not.toBeNull()
    const channels = color?.match(/\d+/g)?.slice(0, 3).map(Number) ?? [255]
    expect(Math.max(...channels), `${name} should use a dark surface`).toBeLessThan(100)
  }
})
