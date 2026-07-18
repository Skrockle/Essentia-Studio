import type { Prediction } from './types'

interface UncertainGenreSuggestionProps {
  prediction: Prediction
  onAccept: (genres: string[]) => void
}

function splitGenreLabel(label: string) {
  return label
    .split('---')
    .map((value) => value.normalize('NFKC').trim())
    .filter(Boolean)
}

function formatConfidence(confidence: number) {
  return new Intl.NumberFormat('de-DE', {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(confidence)
}

export function UncertainGenreSuggestion({
  prediction,
  onAccept,
}: UncertainGenreSuggestionProps) {
  const genres = splitGenreLabel(prediction.label)

  return (
    <aside className="uncertain-genre" aria-label="Unsicherer Genre-Vorschlag">
      <div className="uncertain-genre__heading">
        <span>Unter der Schwelle</span>
        <strong>{formatConfidence(prediction.confidence)}</strong>
      </div>
      <div className="uncertain-genre__tags">
        {genres.map((genre) => <span key={genre}>{genre}</span>)}
      </div>
      <button
        aria-label="Unsichere Genres übernehmen"
        onClick={() => onAccept(genres)}
        type="button"
      >
        Übernehmen
      </button>
    </aside>
  )
}
