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

  const isActive = (tabPath: string) => {
    if (tabPath === basePath) {
      return path === basePath || path === `${basePath}/`
    }
    return path.startsWith(tabPath)
  }

  return (
    <div className="flex gap-1 mb-6 border-b-2 border-[#2D2D44]">
      {tabs.map((tab) => (
        <Link
          key={tab.path}
          to={tab.path}
          className={clsx(
            'px-4 py-2.5 text-sm font-medium border-b-2 -mb-0.5 transition-all',
            isActive(tab.path)
              ? 'border-[#C6F135] text-[#C6F135]'
              : 'border-transparent text-[#8B8BA7] hover:text-white'
          )}
        >
          {tab.label}
        </Link>
      ))}
    </div>
  )
}
