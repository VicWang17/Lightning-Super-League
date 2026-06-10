

interface LeaderboardValueProps {
  value: number
  format: 'int' | 'float1' | 'percent'
}

export function LeaderboardValue({ value, format }: LeaderboardValueProps) {
  if (format === 'percent') {
    return <span>{value.toFixed(1)}%</span>
  }
  if (format === 'float1') {
    return <span>{value.toFixed(1)}</span>
  }
  return <span>{Math.round(value)}</span>
}
