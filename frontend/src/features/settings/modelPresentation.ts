import type { ModelInfo } from '../../api/types'

const roleLabels: Record<string, string[]> = {
  embedding: ['Klangmerkmale (Discogs EffNet)'],
  genre: ['Genre-Erkennung (Discogs 400)'],
  genre_and_embedding: [
    'Klangmerkmale (Discogs EffNet)',
    'Genre-Erkennung (Discogs 400)',
  ],
  mood: ['Mood-Erkennung (MTG Jamendo)'],
  genre_labels: [],
  mood_labels: [],
}

export function presentModels(models: ModelInfo[]): string[] {
  const labels = models.flatMap((model) => {
    const role = model.role
    if (role in roleLabels) return roleLabels[role]
    return ['Zusätzliches Analysemodell']
  })
  return [...new Set(labels)]
}
