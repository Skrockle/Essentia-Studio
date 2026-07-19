import { expect, test } from '@playwright/test'

test('scan, analyze, edit, selectively write, and undo', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Bibliothek scannen' }).click()
  await expect(page.getByText('Scan abgeschlossen')).toBeVisible()

  await page.getByRole('checkbox', { name: 'song-one.wav analysieren' }).check()
  await page.getByRole('button', { name: '1 Titel analysieren' }).click()
  await expect(page.getByText('Analyse abgeschlossen')).toBeVisible()
  const resultRow = page.locator('.result-table tbody tr').first()
  await expect(resultRow.getByText('Electronic', { exact: true })).toBeVisible()
  await expect(resultRow.getByText('House', { exact: true })).toBeVisible()

  await resultRow.getByPlaceholder('Genre ergänzen').fill('Ambient')
  await resultRow.getByPlaceholder('Genre ergänzen').press('Enter')
  await expect(resultRow.getByText('Ambient')).toBeVisible()

  await page.getByRole('checkbox', { name: 'song-one.wav auswählen' }).check()
  await page.getByRole('button', { name: '1 Titel schreiben' }).click()
  await expect(page.getByRole('dialog', { name: 'Tag-Änderungen schreiben' })).toBeVisible()
  const confirmButton = page.getByRole('button', { name: 'Schreiben bestätigen' })
  const colors = await confirmButton.evaluate((button) => {
    const style = getComputedStyle(button)
    return { background: style.backgroundColor, foreground: style.color }
  })
  expect(colors.foreground).not.toBe(colors.background)
  await confirmButton.click()
  await expect(page.getByText('1 verifiziert')).toBeVisible()

  await page.getByRole('checkbox', { name: 'uncertain.wav analysieren' }).check()
  await page.getByRole('button', { name: '1 Titel analysieren' }).click()
  const uncertainRow = page
    .locator('.result-table tbody tr')
    .filter({ hasText: 'uncertain.wav' })
  await expect(uncertainRow.getByText('Unter der Schwelle')).toBeVisible()
  await expect(
    uncertainRow.locator('.tag-editor[data-kind="genre"] .tag-chip'),
  ).toHaveCount(0)
  await uncertainRow.getByRole('button', { name: 'Unsichere Genres übernehmen' }).click()
  await expect(uncertainRow.getByText('Rock', { exact: true })).toBeVisible()
  await expect(
    uncertainRow.locator('.tag-editor[data-kind="genre"] .tag-chip').filter({ hasText: 'Alternative Rock' }),
  ).toBeVisible()

  await expect(page.getByRole('checkbox', { name: 'song-one.wav analysieren' })).toHaveCount(0)
  await page.getByText('Filter', { exact: true }).click()
  await page.getByLabel('Vollständig geschriebene anzeigen').check()
  await expect(page.getByRole('checkbox', { name: 'song-one.wav analysieren' })).toBeVisible()

  await page.getByRole('button', { name: 'Jobs & Verlauf' }).click()
  await page.getByRole('button', { name: 'Tags wiederherstellen' }).click()
  await expect(page.getByText('undone')).toBeVisible()
})
