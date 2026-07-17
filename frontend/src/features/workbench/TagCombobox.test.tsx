import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi } from 'vitest'

import { TagCombobox } from './TagCombobox'

const catalogOptions = ['Ambient', 'Contemporary R&B', 'Nu Contemporary', 'Rock', 'Rockabilly']

function renderCombobox(overrides: Partial<React.ComponentProps<typeof TagCombobox>> = {}) {
  const onAdd = vi.fn()
  render(
    <TagCombobox
      kind="Genre"
      onAdd={onAdd}
      options={catalogOptions}
      selectedValues={[]}
      {...overrides}
    />,
  )
  return { onAdd, input: screen.getByRole('combobox', { name: 'Genre hinzufügen' }) }
}

describe('TagCombobox', () => {
  test('opens unfiltered suggestions on focus without selected values', async () => {
    const user = userEvent.setup()
    const { input } = renderCombobox({ selectedValues: ['Ambient'] })

    await user.click(input)

    expect(screen.getByRole('listbox')).toBeVisible()
    expect(screen.queryByRole('option', { name: 'Ambient' })).not.toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Contemporary R&B' })).toBeVisible()
  })

  test('finds matching catalog values and prioritizes prefixes', async () => {
    const user = userEvent.setup()
    const { input } = renderCombobox({ options: ['Alternative Rock', 'Rock', 'Rockabilly'] })

    await user.type(input, 'rock')

    expect(screen.getAllByRole('option').map((option) => option.textContent)).toEqual([
      'Rock',
      'Rockabilly',
      'Alternative Rock',
    ])
  })

  test('finds Contemporary R&B from a partial query', async () => {
    const user = userEvent.setup()
    const { input } = renderCombobox()

    await user.type(input, 'contemp')

    expect(screen.getByRole('option', { name: 'Contemporary R&B' })).toBeVisible()
  })

  test('updates the active descendant with arrow keys', async () => {
    const user = userEvent.setup()
    const { input } = renderCombobox({ options: ['Rock', 'Rockabilly'] })

    await user.click(input)
    await user.keyboard('{ArrowDown}')
    const firstOptionId = input.getAttribute('aria-activedescendant')
    await user.keyboard('{ArrowDown}')
    const secondOptionId = input.getAttribute('aria-activedescendant')
    await user.keyboard('{ArrowUp}')

    expect(firstOptionId).toBe(screen.getAllByRole('option')[0].id)
    expect(secondOptionId).toBe(screen.getAllByRole('option')[1].id)
    expect(input).toHaveAttribute('aria-activedescendant', firstOptionId)
  })

  test('resets the active option when the filtered suggestions change', async () => {
    const user = userEvent.setup()
    const onAdd = vi.fn()
    const { rerender } = render(
      <TagCombobox kind="Genre" onAdd={onAdd} options={['Rock', 'Rockabilly']} selectedValues={[]} />,
    )
    const input = screen.getByRole('combobox', { name: 'Genre hinzufügen' })

    await user.click(input)
    await user.keyboard('{ArrowDown}{ArrowDown}')
    rerender(<TagCombobox kind="Genre" onAdd={onAdd} options={['Rock']} selectedValues={[]} />)

    expect(input).not.toHaveAttribute('aria-activedescendant')
  })

  test('does not select a replacement suggestion at the same active index', async () => {
    const user = userEvent.setup()
    const onAdd = vi.fn()
    const { rerender } = render(
      <TagCombobox kind="Genre" onAdd={onAdd} options={['Rock', 'Rockabilly']} selectedValues={[]} />,
    )
    const input = screen.getByRole('combobox', { name: 'Genre hinzufügen' })

    await user.click(input)
    await user.keyboard('{ArrowDown}')
    rerender(<TagCombobox kind="Genre" onAdd={onAdd} options={['Jazz', 'Rockabilly']} selectedValues={[]} />)
    await user.keyboard('{Enter}')

    expect(input).not.toHaveAttribute('aria-activedescendant')
    expect(onAdd).not.toHaveBeenCalled()
  })

  test('adds the active option and clears the input on Enter', async () => {
    const user = userEvent.setup()
    const { input, onAdd } = renderCombobox({ options: ['Rock'] })

    await user.type(input, 'rock')
    await user.keyboard('{ArrowDown}{Enter}')

    expect(onAdd).toHaveBeenCalledWith('Rock')
    expect(input).toHaveValue('')
  })

  test('the Plus button adds the typed value instead of the active suggestion', async () => {
    const user = userEvent.setup()
    const { input, onAdd } = renderCombobox({ options: ['Ambient'] })

    await user.type(input, 'Amb')
    await user.keyboard('{ArrowDown}')
    await user.click(screen.getByRole('button', { name: 'Genre hinzufügen' }))

    expect(onAdd).toHaveBeenCalledWith('Amb')
    expect(input).toHaveValue('')
  })

  test('adds a free-form value when Enter has no active option', async () => {
    const user = userEvent.setup()
    const { input, onAdd } = renderCombobox()

    await user.type(input, 'Eigener Stil')
    await user.keyboard('{Enter}')

    expect(onAdd).toHaveBeenCalledWith('Eigener Stil')
    expect(input).toHaveValue('')
  })

  test('closes suggestions on Escape without clearing the input', async () => {
    const user = userEvent.setup()
    const { input } = renderCombobox()

    await user.type(input, 'contemp')
    await user.keyboard('{Escape}')

    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    expect(input).toHaveValue('contemp')
  })

  test('reopens suggestions when the focused input is clicked after Escape', async () => {
    const user = userEvent.setup()
    const { input } = renderCombobox()

    await user.click(input)
    await user.keyboard('{Escape}')
    expect(input).toHaveAttribute('aria-expanded', 'false')

    await user.click(input)

    expect(input).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('listbox')).toBeVisible()
  })

  test('adds a clicked option', async () => {
    const user = userEvent.setup()
    const { input, onAdd } = renderCombobox()

    await user.click(input)
    await user.click(screen.getByRole('option', { name: 'Rock' }))

    expect(onAdd).toHaveBeenCalledWith('Rock')
    expect(input).toHaveValue('')
  })

  test('disables the Plus button for blank input', async () => {
    const user = userEvent.setup()
    const { input } = renderCombobox()
    const addButton = screen.getByRole('button', { name: 'Genre hinzufügen' })

    expect(addButton).toBeDisabled()
    await user.type(input, 'Rock')
    expect(addButton).toBeEnabled()
    await user.clear(input)
    expect(addButton).toBeDisabled()
  })

  test('does not emit a case-insensitive duplicate', async () => {
    const user = userEvent.setup()
    const { input, onAdd } = renderCombobox({ selectedValues: ['Ambient'] })

    await user.type(input, 'ambient')
    await user.keyboard('{Enter}')

    expect(onAdd).not.toHaveBeenCalled()
  })

  test('closes suggestions when the input loses focus', async () => {
    const user = userEvent.setup()
    const { input } = renderCombobox()

    await user.click(input)
    await user.tab()

    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })
})
