import { expect, test } from '@playwright/test'

function rgbChannels(color: string): [number, number, number] {
  const channels = color.match(/\d+/g)?.map(Number) ?? []
  expect(channels).toHaveLength(3)
  return [channels[0], channels[1], channels[2]]
}

function relativeLuminance(channels: [number, number, number]) {
  const linearChannels = channels.map((channel) => {
    const normalized = channel / 255
    return normalized <= 0.04045
      ? normalized / 12.92
      : ((normalized + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * linearChannels[0] + 0.7152 * linearChannels[1] + 0.0722 * linearChannels[2]
}

function contrastRatio(
  first: [number, number, number],
  second: [number, number, number],
) {
  const [lighter, darker] = [relativeLuminance(first), relativeLuminance(second)].sort(
    (left, right) => right - left,
  )
  return (lighter + 0.05) / (darker + 0.05)
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
  const removeElectronic = resultRow.getByRole('button', { name: 'Genre Electronic entfernen' })
  const removeHouse = resultRow.getByRole('button', { name: 'Genre House entfernen' })
  await expect(removeElectronic).toHaveCount(1)
  await expect(removeElectronic).toBeVisible()
  await expect(removeHouse).toHaveCount(1)
  await expect(removeHouse).toBeVisible()

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
  expect(Math.max(...rgbChannels(darkBackground))).toBeLessThan(100)

  await page.getByLabel('Farbschema').selectOption('light')
  const lightColors = await listbox.evaluate((element) => {
    const styles = getComputedStyle(element)
    return { background: styles.backgroundColor, foreground: styles.color }
  })
  expect(contrastRatio(rgbChannels(lightColors.foreground), rgbChannels(lightColors.background))).toBeGreaterThanOrEqual(4.5)
})
