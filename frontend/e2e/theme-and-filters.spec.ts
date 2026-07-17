import { expect, test } from '@playwright/test'

async function expectDarkBackgrounds(
  page: import('@playwright/test').Page,
  selectors: string[],
) {
  for (const selector of selectors) {
    const surface = page.locator(selector).first()
    await expect(surface, `${selector} should exist`).toBeVisible()
    const channels = await surface.evaluate((element) => {
      return getComputedStyle(element).backgroundColor.match(/\d+/g)?.slice(0, 3).map(Number) ?? [255]
    })
    expect(Math.max(...channels), `${selector} should use a dark background`).toBeLessThan(100)
  }
}

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
  await expectDarkBackgrounds(page, [
    '.app-nav',
    '.library-table th',
    '.selection-toolbar',
    '.result-table th',
    '.tag-editor input',
    '.format-badge',
    '.tag-chip',
  ])

  const libraryDivider = await page.locator('.library-table tbody tr').first().evaluate((row) => ({
    rowShadow: getComputedStyle(row).boxShadow,
    cellBorder: getComputedStyle(row.querySelector('td')!).borderBottomWidth,
  }))
  expect(libraryDivider.rowShadow).not.toBe('none')
  expect(libraryDivider.cellBorder).toBe('0px')

  const resultDivider = await page.locator('.result-table tbody tr').first().evaluate((row) => ({
    rowShadow: getComputedStyle(row).boxShadow,
    cellBorder: getComputedStyle(row.querySelector('td')!).borderBottomWidth,
  }))
  expect(resultDivider.rowShadow).not.toBe('none')
  expect(resultDivider.cellBorder).toBe('0px')

  await page.getByRole('button', { name: 'Playlists' }).click()
  await expectDarkBackgrounds(page, ['.preset-grid article button'])

  await page.getByRole('button', { name: 'Einstellungen' }).click()
  await expectDarkBackgrounds(page, [
    '.path-status',
    '.status-label',
    '.model-status',
  ])
})
