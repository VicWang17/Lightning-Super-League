import { BatteryFull, BatteryMedium, BatteryLow } from './pixel-icons'

interface FatigueStatusProps {
  fatigue: number
  className?: string
  size?: number
}

const STATUS = [
  { max: 35, Icon: BatteryFull, color: '#9ECF45', label: '精神' },
  { max: 70, Icon: BatteryMedium, color: '#D7A94A', label: '正常' },
  { max: 100, Icon: BatteryLow, color: '#D75A4A', label: '疲劳' },
]

export function FatigueStatus({ fatigue, className, size = 16 }: FatigueStatusProps) {
  const state = STATUS.find((s) => fatigue <= s.max) || STATUS[STATUS.length - 1]
  const Icon = state.Icon
  return (
    <span className={className} title={state.label} style={{ display: 'inline-flex', alignItems: 'center' }}>
      <Icon style={{ color: state.color, width: size, height: size }} />
    </span>
  )
}
