export function formatDollar(value: number): string {
  if (Math.abs(value) >= 1_000_000)
    return `$${(value / 1_000_000).toFixed(1)}m`;
  if (Math.abs(value) >= 1_000)
    return `$${(value / 1_000).toFixed(0)}k`;
  return `$${value.toFixed(0)}`;
}

export function formatPercent(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

export function formatDate(isoDate: string): string {
  return isoDate.slice(0, 7); // "YYYY-MM"
}
