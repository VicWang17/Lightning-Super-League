type CupBadgeSize = 'sm' | 'md' | 'lg'

interface CupBadgeProps {
  code?: string
  size?: CupBadgeSize
  className?: string
  title?: string
}

const SIZE_CLASS: Record<CupBadgeSize, string> = {
  sm: 'w-6 h-6',
  md: 'w-12 h-12',
  lg: 'w-16 h-16',
}

const CUP_PALETTE = {
  LIGHTNING_CUP: {
    base: '#F7C948',
    mid: '#C17826',
    dark: '#2A1607',
    light: '#FFF2A8',
    accent: '#C6F135',
    glow: '#0D7377',
  },
  JENNY_CUP: {
    base: '#2FC083',
    mid: '#146B55',
    dark: '#08231F',
    light: '#91F0C5',
    accent: '#59D6D6',
    glow: '#C6F135',
  },
} as const

function getPalette(code?: string) {
  return CUP_PALETTE[(code || 'LIGHTNING_CUP') as keyof typeof CUP_PALETTE] || CUP_PALETTE.LIGHTNING_CUP
}

export function CupBadge({ code, size = 'md', className = '', title }: CupBadgeProps) {
  const colors = getPalette(code)
  const isLightning = code !== 'JENNY_CUP'
  const badgeTitle = title || `${code || 'LIGHTNING_CUP'} cup badge`

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
      {isLightning ? (
        <>
          <rect x="18" y="2" width="28" height="4" fill="#050609" />
          <rect x="12" y="6" width="40" height="10" fill="#050609" />
          <rect x="8" y="16" width="48" height="24" fill="#050609" />
          <rect x="14" y="40" width="36" height="8" fill="#050609" />
          <rect x="22" y="48" width="20" height="8" fill="#050609" />
          <rect x="28" y="56" width="8" height="4" fill="#050609" />

          <rect x="18" y="8" width="28" height="4" fill={colors.light} />
          <rect x="14" y="12" width="36" height="10" fill={colors.base} />
          <rect x="12" y="22" width="40" height="16" fill={colors.mid} />
          <rect x="18" y="38" width="28" height="8" fill={colors.dark} />
          <rect x="26" y="46" width="12" height="8" fill={colors.dark} />

          <rect x="38" y="10" width="8" height="4" fill={colors.accent} />
          <rect x="34" y="14" width="8" height="8" fill={colors.accent} />
          <rect x="30" y="22" width="8" height="6" fill={colors.accent} />
          <rect x="22" y="28" width="12" height="4" fill={colors.accent} />
          <rect x="28" y="32" width="8" height="8" fill={colors.light} />
          <rect x="24" y="40" width="8" height="4" fill={colors.light} />
          <rect x="14" y="22" width="4" height="16" fill="#FFFFFF" opacity="0.16" />
          <rect x="48" y="22" width="4" height="16" fill="#000000" opacity="0.28" />
          <rect x="18" y="54" width="28" height="4" fill={colors.mid} />
        </>
      ) : (
        <>
          <rect x="28" y="2" width="8" height="4" fill="#050609" />
          <rect x="20" y="6" width="24" height="6" fill="#050609" />
          <rect x="14" y="12" width="36" height="8" fill="#050609" />
          <rect x="8" y="20" width="48" height="16" fill="#050609" />
          <rect x="14" y="36" width="36" height="8" fill="#050609" />
          <rect x="22" y="44" width="20" height="8" fill="#050609" />
          <rect x="16" y="52" width="32" height="8" fill="#050609" />

          <rect x="28" y="6" width="8" height="4" fill={colors.glow} />
          <rect x="22" y="10" width="20" height="4" fill={colors.light} />
          <rect x="16" y="14" width="32" height="8" fill={colors.accent} />
          <rect x="12" y="22" width="40" height="10" fill={colors.base} />
          <rect x="18" y="32" width="28" height="8" fill={colors.mid} />
          <rect x="26" y="40" width="12" height="10" fill={colors.dark} />
          <rect x="20" y="54" width="24" height="4" fill={colors.mid} />

          <rect x="4" y="22" width="8" height="8" fill="#050609" />
          <rect x="52" y="22" width="8" height="8" fill="#050609" />
          <rect x="6" y="24" width="6" height="4" fill={colors.mid} />
          <rect x="52" y="24" width="6" height="4" fill={colors.mid} />

          <rect x="28" y="18" width="8" height="4" fill={colors.light} />
          <rect x="24" y="22" width="16" height="4" fill={colors.glow} />
          <rect x="28" y="26" width="8" height="4" fill={colors.light} />
          <rect x="18" y="20" width="4" height="14" fill="#FFFFFF" opacity="0.15" />
          <rect x="46" y="20" width="4" height="14" fill="#000000" opacity="0.28" />
        </>
      )}
    </svg>
  )
}
