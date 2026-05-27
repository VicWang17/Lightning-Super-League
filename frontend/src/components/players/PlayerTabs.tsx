import { Link, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'

interface PlayerTabsProps {
  playerId: string
}

export function PlayerTabs({ playerId }: PlayerTabsProps) {
  const location = useLocation()
  const isHistory = location.pathname.endsWith('/history')

  const tabs = [
    { path: `/players/${playerId}`, label: '球员档案' },
    { path: `/players/${playerId}/history`, label: '生涯历史' },
  ]

  return (
    <div className="flex gap-1 mb-6 border-b-2 border-[#2D2D44]">
      {tabs.map((tab) => (
        <Link
          key={tab.path}
          to={tab.path}
          className={clsx(
            'px-4 py-2.5 text-sm font-medium border-b-2 -mb-0.5 transition-all',
            (tab.path === `/players/${playerId}` && !isHistory) || (tab.path.endsWith('/history') && isHistory)
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
