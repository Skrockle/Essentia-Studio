import { expect, test } from '@playwright/test'

test('scan, analyze, edit, selectively write, and undo', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Bibliothek scannen' }).click()
  await expect(page.getByText('Scan abgeschlossen')).toBeVisible()

  await page.getByRole('checkbox', { name: 'Alle gescannten Titel analysieren' }).check()
  await page.getByRole('button', { name: '1 Titel analysieren' }).click()
  await expect(page.getByText('Analyse abgeschlossen')).toBeVisible()
  await expect(page.getByText('Electronic; House')).toBeVisible()

  await page.getByPlaceholder('Genre ergänzen').fill('Ambient')
  await page.getByPlaceholder('Genre ergänzen').press('Enter')
  await expect(page.getByText('Ambient')).toBeVisible()

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

  await expect(page.getByRole('checkbox', { name: 'song-one.wav analysieren' })).toHaveCount(0)
  await page.getByText('Filter', { exact: true }).click()
  await page.getByLabel('Vollständig geschriebene anzeigen').check()
  await expect(page.getByRole('checkbox', { name: 'song-one.wav analysieren' })).toBeVisible()

  await page.getByRole('button', { name: 'Jobs & Verlauf' }).click()
  await page.getByRole('button', { name: 'Tags wiederherstellen' }).click()
  await expect(page.getByText('undone')).toBeVisible()
})
