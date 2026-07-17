import { expect, test } from '@playwright/test'

function colorChannels(color: string) {
  return color.match(/\d+/g)?.slice(0, 3).map(Number) ?? []
}

test('splits hierarchical tags and edits drafts with catalog suggestions', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Bibliothek scannen' }).click()
  await expect(page.getByText('Scan abgeschlossen')).toBeVisible()

  await page.getByRole('checkbox', { name: 'Alle gescannten Titel analysieren' }).check()
  await page.getByRole('button', { name: '1 Titel analysieren' }).click()
  await expect(page.getByText('Analyse abgeschlossen')).toBeVisible()

  const resultRow = page.locator('.result-table tbody tr').first()
  await expect(resultRow.getByText('Electronic', { exact: true })).toBeVisible()
  await expect(resultRow.getByText('House', { exact: true })).toBeVisible()

  const genreInput = resultRow.getByRole('combobox', { name: 'Genre hinzufügen' })
  const rowBeforePopup = await resultRow.boundingBox()
  expect(rowBeforePopup).not.toBeNull()
  await genreInput.focus()
  await expect(page.getByRole('option', { name: 'Ambient', exact: true })).toBeVisible()
  const rowWithPopup = await resultRow.boundingBox()
  expect(rowWithPopup).not.toBeNull()
  expect(rowWithPopup?.height).toBe(rowBeforePopup?.height)

  await genreInput.fill('Amb')
  await genreInput.press('ArrowDown')
  await genreInput.press('Enter')
  await expect(resultRow.getByText('Ambient', { exact: true })).toBeVisible()

  await genreInput.fill('Eigener Stil')
  await genreInput.press('Enter')
  await expect(resultRow.getByText('Eigener Stil', { exact: true })).toBeVisible()

  const moodInput = resultRow.getByRole('combobox', { name: 'Mood hinzufügen' })
  await moodInput.focus()
  await page.getByRole('option', { name: 'Sad', exact: true }).click()
  await expect(resultRow.getByText('Sad', { exact: true })).toBeVisible()

  const draft = await page.evaluate(async () => {
    const response = await fetch('/api/results')
    const results = await response.json()
    return results.items[0].draft
  })
  expect(draft).toMatchObject({
    genres: ['Electronic', 'House', 'Ambient', 'Eigener Stil'],
    moods: ['Happy', 'Sad'],
  })

  await genreInput.focus()
  const listbox = page.getByRole('listbox')
  await expect(listbox).toBeVisible()
  await page.getByLabel('Farbschema').selectOption('dark')
  const darkBackground = await listbox.evaluate((element) => getComputedStyle(element).backgroundColor)
  expect(Math.max(...colorChannels(darkBackground))).toBeLessThan(100)

  await page.getByLabel('Farbschema').selectOption('light')
  const lightColors = await listbox.evaluate((element) => {
    const styles = getComputedStyle(element)
    return { background: styles.backgroundColor, foreground: styles.color }
  })
  expect(lightColors.foreground).not.toBe(lightColors.background)
})
