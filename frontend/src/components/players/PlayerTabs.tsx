import { Link, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'

interface PlayerTabsProps {
  playerId: string
}

export function PlayerTabs({ playerId }: PlayerTabsProps) {
  const location = useLocation()
  const path = location.pathname

  const isTeamRoute = path.startsWith('/team/players/')
  const basePath = isTeamRoute ? `/team/players/${playerId}` : `/players/${playerId}`

  const tabs = [
    { path: basePath, label: '球员档案' },
    { path: `${basePath}/history`, label: '生涯历史' },
    { path: `${basePath}/transfers`, label: '转会记录' },
    { path: `${basePath}/growth`, label: '成长曲线' },
  ]

  return (
    <div className="flex flex-wrap gap-2 mb-6">
      {tabs.map((tab) => {
        const isActive =
          tab.path === basePath
            ? path === basePath || path === `${basePath}/`
            : path.startsWith(tab.path)

        return (
          <Link
            key={tab.path}
            to={tab.path}
            className={clsx(
              'px-4 py-2 font-medium text-sm transition-all duration-200 flex items-center gap-2',
              isActive
                ? 'bg-[#C6F135] text-[#0A0A0F] border-2 border-transparent font-bold shadow-pixel-green'
                : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover border-2 border-transparent'
            )}
          >
            {tab.label}
          </Link>
        )
      })}
    </div>
  )
}
