type LeagueBadgeSize = 'sm' | 'md' | 'lg'

interface LeagueBadgeProps {
  systemCode?: string
  level?: number
  size?: LeagueBadgeSize
  className?: string
  title?: string
}

const SIZE_CLASS: Record<LeagueBadgeSize, string> = {
  sm: 'w-6 h-6',
  md: 'w-12 h-12',
  lg: 'w-16 h-16',
}

const SYSTEM_PALETTE = {
  EAST: {
    base: '#B92E34',
    mid: '#74192A',
    dark: '#290B14',
    light: '#FF6A55',
    accent: '#F7C948',
    trim: '#F08A24',
  },
  WEST: {
    base: '#C17826',
    mid: '#70411E',
    dark: '#251409',
    light: '#F5B65A',
    accent: '#53A6C8',
    trim: '#E5D08A',
  },
  SOUTH: {
    base: '#189A70',
    mid: '#0E594E',
    dark: '#08231F',
    light: '#5EE6A8',
    accent: '#59D6D6',
    trim: '#C6F135',
  },
  NORTH: {
    base: '#3C7EDB',
    mid: '#1F3E75',
    dark: '#091426',
    light: '#8BC8FF',
    accent: '#D8ECFF',
    trim: '#8EE3F5',
  },
} as const

const LEVEL_METAL: Record<number, { main: string; shadow: string; light: string }> = {
  1: { main: '#F7C948', shadow: '#A65F13', light: '#FFF2A8' },
  2: { main: '#BCC7D6', shadow: '#5D6877', light: '#F1F5F9' },
  3: { main: '#C8793E', shadow: '#6F351C', light: '#F2B279' },
  4: { main: '#8D8172', shadow: '#3B352F', light: '#C9B8A1' },
}

function getPalette(systemCode?: string) {
  return SYSTEM_PALETTE[(systemCode || 'EAST') as keyof typeof SYSTEM_PALETTE] || SYSTEM_PALETTE.EAST
}

function ShieldBase({ colors }: { colors: ReturnType<typeof getPalette> }) {
  return (
    <>
      <rect x="16" y="0" width="32" height="4" fill="#050609" />
      <rect x="8" y="4" width="48" height="8" fill="#050609" />
      <rect x="4" y="12" width="56" height="28" fill="#050609" />
      <rect x="8" y="40" width="48" height="8" fill="#050609" />
      <rect x="16" y="48" width="32" height="8" fill="#050609" />
      <rect x="24" y="56" width="16" height="4" fill="#050609" />

      <rect x="16" y="8" width="32" height="4" fill={colors.light} />
      <rect x="12" y="12" width="40" height="8" fill={colors.base} />
      <rect x="8" y="20" width="48" height="18" fill={colors.base} />
      <rect x="12" y="38" width="40" height="8" fill={colors.mid} />
      <rect x="20" y="46" width="24" height="8" fill={colors.mid} />
      <rect x="28" y="54" width="8" height="2" fill={colors.mid} />

      <rect x="12" y="20" width="4" height="18" fill={colors.light} opacity="0.5" />
      <rect x="48" y="20" width="4" height="18" fill={colors.dark} opacity="0.65" />
      <rect x="20" y="12" width="24" height="4" fill="#FFFFFF" opacity="0.16" />
    </>
  )
}

function LevelMark({ level }: { level: number }) {
  const metal = LEVEL_METAL[level] || LEVEL_METAL[4]

  if (level === 1) {
    return (
      <>
        <rect x="20" y="4" width="6" height="8" fill={metal.main} />
        <rect x="30" y="0" width="6" height="12" fill={metal.light} />
        <rect x="40" y="4" width="6" height="8" fill={metal.main} />
        <rect x="18" y="12" width="30" height="4" fill={metal.shadow} />
        <rect x="22" y="12" width="22" height="2" fill={metal.light} />
      </>
    )
  }

  if (level === 2) {
    return (
      <>
        <rect x="18" y="10" width="28" height="4" fill={metal.main} />
        <rect x="22" y="16" width="20" height="3" fill={metal.shadow} />
        <rect x="26" y="48" width="4" height="4" fill={metal.light} />
        <rect x="34" y="48" width="4" height="4" fill={metal.light} />
      </>
    )
  }

  if (level === 3) {
    return (
      <>
        <rect x="18" y="12" width="8" height="4" fill={metal.main} />
        <rect x="26" y="16" width="8" height="4" fill={metal.main} />
        <rect x="34" y="20" width="8" height="4" fill={metal.shadow} />
        <rect x="42" y="24" width="4" height="4" fill={metal.shadow} />
        <rect x="28" y="48" width="8" height="4" fill={metal.light} />
      </>
    )
  }

  return (
    <>
      <rect x="18" y="12" width="6" height="4" fill={metal.light} />
      <rect x="30" y="12" width="6" height="4" fill={metal.main} />
      <rect x="42" y="12" width="6" height="4" fill={metal.shadow} />
      <rect x="24" y="48" width="16" height="4" fill={metal.main} />
    </>
  )
}

function SystemMark({ systemCode, colors }: { systemCode?: string; colors: ReturnType<typeof getPalette> }) {
  if (systemCode === 'WEST') {
    return (
      <>
        <rect x="25" y="20" width="14" height="4" fill={colors.trim} />
        <rect x="21" y="24" width="22" height="4" fill={colors.light} />
        <rect x="17" y="28" width="30" height="4" fill={colors.trim} />
        <rect x="20" y="34" width="24" height="4" fill={colors.dark} opacity="0.55" />
        <rect x="16" y="40" width="32" height="4" fill={colors.accent} />
      </>
    )
  }

  if (systemCode === 'SOUTH') {
    return (
      <>
        <rect x="19" y="24" width="8" height="4" fill={colors.trim} />
        <rect x="27" y="20" width="4" height="20" fill={colors.trim} />
        <rect x="31" y="24" width="8" height="4" fill={colors.light} />
        <rect x="35" y="28" width="8" height="4" fill={colors.trim} />
        <rect x="17" y="40" width="12" height="4" fill={colors.accent} />
        <rect x="29" y="36" width="12" height="4" fill={colors.accent} />
        <rect x="41" y="40" width="6" height="4" fill={colors.accent} />
      </>
    )
  }

  if (systemCode === 'NORTH') {
    return (
      <>
        <rect x="30" y="18" width="4" height="24" fill={colors.accent} />
        <rect x="26" y="22" width="12" height="4" fill={colors.accent} />
        <rect x="28" y="42" width="8" height="4" fill={colors.trim} />
        <rect x="18" y="38" width="8" height="6" fill={colors.light} />
        <rect x="26" y="32" width="8" height="12" fill={colors.light} />
        <rect x="34" y="36" width="12" height="8" fill={colors.light} />
        <rect x="22" y="42" width="24" height="4" fill={colors.mid} />
      </>
    )
  }

  return (
    <>
      <rect x="36" y="16" width="8" height="4" fill={colors.accent} />
      <rect x="32" y="20" width="8" height="4" fill={colors.accent} />
      <rect x="28" y="24" width="8" height="4" fill={colors.accent} />
      <rect x="24" y="28" width="12" height="4" fill={colors.accent} />
      <rect x="28" y="32" width="8" height="4" fill={colors.trim} />
      <rect x="24" y="36" width="8" height="8" fill={colors.trim} />
      <rect x="36" y="28" width="6" height="6" fill={colors.light} />
    </>
  )
}

export function LeagueBadge({ systemCode, level = 0, size = 'md', className = '', title }: LeagueBadgeProps) {
  const colors = getPalette(systemCode)
  const badgeTitle = title || `${systemCode || 'EAST'} league badge`

  return (
    <svg
      className={`${SIZE_CLASS[size]} ${className}`}
      viewBox="0 0 64 64"
      role="img"
      aria-label={badgeTitle}
      shapeRendering="crispEdges"
      xmlns="http://www.w3.org/2000/svg"
    >
      <title>{badgeTitle}</title>
      <ShieldBase colors={colors} />
      <SystemMark systemCode={systemCode} colors={colors} />
      {level > 0 && <LevelMark level={level} />}
      <rect x="8" y="20" width="4" height="18" fill="#FFFFFF" opacity="0.12" />
      <rect x="52" y="20" width="4" height="18" fill="#000000" opacity="0.28" />
    </svg>
  )
}
