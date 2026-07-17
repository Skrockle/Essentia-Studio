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
  await page.getByRole('button', { name: 'Schreiben bestätigen' }).click()
  await expect(page.getByText('1 verifiziert')).toBeVisible()

  await page.getByRole('button', { name: 'Jobs & Verlauf' }).click()
  await page.getByRole('button', { name: 'Tags wiederherstellen' }).click()
  await expect(page.getByText('undone')).toBeVisible()
})
