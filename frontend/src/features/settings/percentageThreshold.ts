export function thresholdToPercentage(threshold: number): number {
  return Math.round(threshold * 100)
}

export function percentageToThreshold(percentage: number): number | null {
  if (!Number.isInteger(percentage) || percentage < 0 || percentage > 100) return null
  return percentage / 100
}
