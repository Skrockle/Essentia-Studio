import {
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
  type KeyboardEvent,
} from 'react'
import { createPortal } from 'react-dom'
import { Plus } from 'lucide-react'

interface TagComboboxProps {
  kind: 'Genre' | 'Mood'
  options: string[]
  selectedValues: string[]
  onAdd: (value: string) => void
}

const maximumSuggestions = 8
const maximumPopupHeight = 212
const popupGap = 4
const viewportPadding = 8

function popupPosition(anchor: HTMLFormElement): CSSProperties {
  const anchorBounds = anchor.getBoundingClientRect()
  const spaceBelow = window.innerHeight - anchorBounds.bottom - popupGap - viewportPadding
  const spaceAbove = anchorBounds.top - popupGap - viewportPadding
  const openAbove = spaceBelow < maximumPopupHeight && spaceAbove > spaceBelow
  const availableHeight = Math.max(0, openAbove ? spaceAbove : spaceBelow)
  const width = Math.min(anchorBounds.width, window.innerWidth - viewportPadding * 2)
  return {
    bottom: openAbove ? window.innerHeight - anchorBounds.top + popupGap : undefined,
    left: Math.min(
      Math.max(viewportPadding, anchorBounds.left),
      window.innerWidth - viewportPadding - width,
    ),
    maxHeight: Math.min(maximumPopupHeight, availableHeight),
    top: openAbove ? undefined : anchorBounds.bottom + popupGap,
    width,
  }
}

function includesValue(values: string[], candidate: string) {
  const normalizedCandidate = candidate.toLocaleLowerCase()
  return values.some((value) => value.toLocaleLowerCase() === normalizedCandidate)
}

export function TagCombobox({ kind, options, selectedValues, onAdd }: TagComboboxProps) {
  const inputId = useId()
  const listboxId = useId()
  const formRef = useRef<HTMLFormElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [open, setOpen] = useState(false)
  const [listboxPosition, setListboxPosition] = useState<CSSProperties>({})
  const [inputValue, setInputValue] = useState('')
  const [activeIndex, setActiveIndex] = useState(-1)
  const [activeSuggestionSignature, setActiveSuggestionSignature] = useState('')
  const suggestions = useMemo(() => {
    const query = inputValue.trim().toLocaleLowerCase()
    const unselectedOptions = options.filter((option) => !includesValue(selectedValues, option))
    if (!query) return unselectedOptions.slice(0, maximumSuggestions)

    const prefixMatches = unselectedOptions.filter((option) => option.toLocaleLowerCase().startsWith(query))
    const substringMatches = unselectedOptions.filter(
      (option) => !option.toLocaleLowerCase().startsWith(query) && option.toLocaleLowerCase().includes(query),
    )
    return [...prefixMatches, ...substringMatches].slice(0, maximumSuggestions)
  }, [inputValue, options, selectedValues])
  const suggestionSignature = suggestions.join('\u0000')
  const visibleActiveIndex = activeSuggestionSignature === suggestionSignature && activeIndex >= 0 && activeIndex < suggestions.length
    ? activeIndex
    : -1
  const activeOptionId = visibleActiveIndex >= 0 ? `${listboxId}-option-${visibleActiveIndex}` : undefined

  useLayoutEffect(() => {
    if (!open) return
    function updateListboxPosition() {
      if (formRef.current) setListboxPosition(popupPosition(formRef.current))
    }
    updateListboxPosition()
    window.addEventListener('resize', updateListboxPosition)
    window.addEventListener('scroll', updateListboxPosition, true)
    return () => {
      window.removeEventListener('resize', updateListboxPosition)
      window.removeEventListener('scroll', updateListboxPosition, true)
    }
  }, [open])

  function updateActiveIndex(nextIndex: number) {
    setActiveIndex(nextIndex)
    setActiveSuggestionSignature(suggestionSignature)
  }

  function resetInput() {
    setInputValue('')
    updateActiveIndex(-1)
    setOpen(false)
  }

  function addValue(value: string) {
    const normalizedValue = value.trim()
    if (!normalizedValue || includesValue(selectedValues, normalizedValue)) return false
    onAdd(normalizedValue)
    resetInput()
    return true
  }

  function addTypedValue() {
    if (addValue(inputValue)) inputRef.current?.focus()
  }

  function submitValue(event: FormEvent) {
    event.preventDefault()
    const activeOption = suggestions[visibleActiveIndex]
    addValue(activeOption ?? inputValue)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setOpen(true)
      updateActiveIndex(Math.min(visibleActiveIndex + 1, suggestions.length - 1))
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      updateActiveIndex(visibleActiveIndex > 0 ? visibleActiveIndex - 1 : -1)
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      updateActiveIndex(-1)
      setOpen(false)
    }
  }

  return (
    <form className="tag-editor__form" onSubmit={submitValue} ref={formRef}>
      <label className="sr-only" htmlFor={inputId}>
        {kind} hinzufügen
      </label>
      <input
        aria-activedescendant={activeOptionId}
        aria-autocomplete="list"
        aria-controls={listboxId}
        aria-expanded={open}
        id={inputId}
        maxLength={120}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen(true)}
        onChange={(event) => {
          setInputValue(event.target.value)
          updateActiveIndex(-1)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={`${kind} ergänzen`}
        ref={inputRef}
        role="combobox"
        value={inputValue}
      />
      <button
        aria-label={`${kind} hinzufügen`}
        disabled={!inputValue.trim()}
        onClick={addTypedValue}
        type="button"
      >
        <Plus aria-hidden="true" size={13} />
      </button>
      {open && createPortal(
        <div
          className="tag-editor__suggestions"
          data-kind={kind.toLocaleLowerCase()}
          id={listboxId}
          role="listbox"
          style={listboxPosition}
        >
          {suggestions.map((suggestion, index) => (
            <button
              aria-selected={index === visibleActiveIndex}
              className="tag-editor__suggestion"
              id={`${listboxId}-option-${index}`}
              key={suggestion}
              onClick={() => addValue(suggestion)}
              onMouseDown={(event) => event.preventDefault()}
              role="option"
              type="button"
            >
              {suggestion}
            </button>
          ))}
        </div>,
        document.body,
      )}
    </form>
  )
}
