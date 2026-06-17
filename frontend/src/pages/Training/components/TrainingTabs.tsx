import { NavLink, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  Calendar,
  Clock,
  Target,
  TrendingUp,
  Zap,
} from '../../../components/ui/pixel-icons'

const TABS = [
  { path: '/training/weekly', label: '周计划', icon: Target },
  { path: '/training/calendar', label: '日程', icon: Calendar },
  { path: '/training/fatigue', label: '疲劳', icon: Zap },
  { path: '/training/history', label: '历史', icon: Clock },
  { path: '/training/progress', label: '成长曲线', icon: TrendingUp },
]

export function TrainingTabs() {
  const location = useLocation()

  return (
    <nav className="flex flex-wrap gap-2 mb-6">
      {TABS.map((tab) => {
        const Icon = tab.icon
        const isActive = location.pathname.startsWith(tab.path)
        return (
          <NavLink
            key={tab.path}
            to={tab.path}
            end
            className={clsx(
              'px-4 py-2 text-sm font-medium border-2 transition-all flex items-center gap-2',
              isActive
                ? 'bg-[#C6F135] text-[#0A0A0F] border-[#C6F135]'
                : 'bg-[#12121A] text-[#8B8BA7] border-[#2D2D44] hover:border-[#0D7377] hover:text-white'
            )}
          >
            <Icon className="w-4 h-4" />
            {tab.label}
          </NavLink>
        )
      })}
    </nav>
  )
}
