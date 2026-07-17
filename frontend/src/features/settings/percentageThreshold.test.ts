import { expect, test } from 'vitest'

import { percentageToThreshold, thresholdToPercentage } from './percentageThreshold'

test('converts normalized thresholds to whole percentages', () => {
  expect(thresholdToPercentage(0.25)).toBe(25)
  expect(thresholdToPercentage(0.1)).toBe(10)
})

test('converts valid percentages without accepting invalid values', () => {
  expect(percentageToThreshold(25)).toBe(0.25)
  expect(percentageToThreshold(10)).toBe(0.1)
  expect(percentageToThreshold(Number.NaN)).toBeNull()
  expect(percentageToThreshold(-1)).toBeNull()
  expect(percentageToThreshold(101)).toBeNull()
  expect(percentageToThreshold(10.5)).toBeNull()
})
