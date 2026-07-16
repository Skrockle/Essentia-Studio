import { expect, test } from '@playwright/test'

test('creates and deletes a This is playlist', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Playlists' }).click()
  await page.getByRole('tab', { name: 'This is …' }).click()
  await page.getByLabel('Album-Künstler').fill('Björk')
  await page.getByLabel('Methode').selectOption('greatest_hits')
  await page.getByLabel('Dateiname').fill('this-is-bjork.nsp')
  await page.getByRole('button', { name: 'Vorschau erzeugen' }).click()
  await expect(page.getByText('This is Björk', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Playlist speichern' }).click()
  await expect(page.getByText('this-is-bjork.nsp gespeichert')).toBeVisible()
  await page.getByRole('button', { name: 'this-is-bjork.nsp löschen' }).click()
  await page.getByRole('button', { name: 'Löschen bestätigen' }).click()
  await expect(page.getByRole('button', { name: 'this-is-bjork.nsp löschen' })).not.toBeVisible()
})
