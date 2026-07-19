import { expect, test } from 'vitest'

import { presentModels } from './modelPresentation'

test('turns technical model files into concise user-facing capabilities', () => {
  const models = presentModels([
    { name: 'discogs-effnet-bs64-1.pb', role: 'embedding' },
    { name: 'genre_discogs400-discogs-effnet-1.pb', role: 'genre' },
    { name: 'genre_discogs400-discogs-effnet-1.json', role: 'genre_labels' },
    { name: 'mtg_jamendo_moodtheme-discogs-effnet-1.pb', role: 'mood' },
  ])

  expect(models).toEqual([
    'Klangmerkmale (Discogs EffNet)',
    'Genre-Erkennung (Discogs 400)',
    'Mood-Erkennung (MTG Jamendo)',
  ])
  expect(models.join(' ')).not.toContain('.pb')
})

test('presents the combined ONNX EffNet outputs as both capabilities', () => {
  const models = presentModels([
    { name: 'discogs-effnet-bsdynamic-1.onnx', role: 'genre_and_embedding' },
    { name: 'mtg_jamendo_moodtheme-discogs-effnet-1.onnx', role: 'mood' },
  ])

  expect(models).toEqual([
    'Klangmerkmale (Discogs EffNet)',
    'Genre-Erkennung (Discogs 400)',
    'Mood-Erkennung (MTG Jamendo)',
  ])
})
