import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  Home as LayoutDashboard,
  Users,
  Trophy,
  Calendar as CalendarDays,
  Transfer as ArrowLeftRight,
  Tree as Sprout,
  Logout as LogOut,
  Sword as Swords,
  Wallet,
  Zap,
  ChevronDown,
  ChevronRight as ChevronRightIcon,
} from '../ui/pixel-icons'
import { useAuthStore } from '../../stores/auth'
import api from '../../api/client'
import type { Team } from '../../types/team'
import type { CupCompetition } from '../../types/cup'

interface MenuChild {
  path: string
  label: string
}

interface MenuItem {
  path: string
  label: string
  icon: React.ElementType
  children?: MenuChild[]
}

const staticMenuItems: MenuItem[] = [
  { path: '/dashboard', label: '总览', icon: LayoutDashboard },
  {
    path: '/team',
    label: '球队',
    icon: Users,
    children: [
      { path: '/team/players', label: '球员' },
      { path: '/team/tactics', label: '战术' },
    ],
  },
  { path: '/match/schedule', label: '赛程', icon: CalendarDays },
  {
    path: '/transfer',
    label: '转会',
    icon: ArrowLeftRight,
    children: [
      { path: '/transfer/market', label: '拍卖市场' },
      { path: '/transfer/free-market', label: '自由市场' },
      { path: '/transfer/watchlist', label: '关注列表' },
      { path: '/transfer/history', label: '转会历史' },
    ],
  },
  {
    path: '/youth',
    label: '青训',
    icon: Sprout,
    children: [
      { path: '/youth/academy', label: '青训营' },
      { path: '/youth/draft', label: '选秀大会' },
      { path: '/youth/young-players', label: '年轻球员' },
    ],
  },
  {
    path: '/finance',
    label: '财务',
    icon: Wallet,
    children: [
      { path: '/finance/overview', label: '财务总览' },
      { path: '/finance/budget', label: '预算规划' },
      { path: '/finance/income', label: '收入明细' },
      { path: '/finance/expense', label: '支出明细' },
    ],
  },
]

function Sidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  const [myLeagueId, setMyLeagueId] = useState<string | null>(null)
  const [myCupId, setMyCupId] = useState<string | null>(null)
  const [idsLoading, setIdsLoading] = useState(true)

  useEffect(() => {
    const fetchIds = async () => {
      setIdsLoading(true)
      const [teamRes, cupRes] = await Promise.allSettled([
        api.get<Team>('/teams/my-team'),
        api.get<CupCompetition>('/cups/my-team'),
      ])
      if (teamRes.status === 'fulfilled' && teamRes.value.success && teamRes.value.data?.league_id) {
        setMyLeagueId(teamRes.value.data.league_id)
      }
      if (cupRes.status === 'fulfilled' && cupRes.value.success && cupRes.value.data?.id) {
        setMyCupId(cupRes.value.data.id)
      }
      setIdsLoading(false)
    }
    fetchIds()
  }, [])

  const menuItems: MenuItem[] = [
    ...staticMenuItems.slice(0, 2),
    {
      path: '/training',
      label: '训练',
      icon: Zap,
      children: [
        { path: '/training/weekly', label: '本周训练' },
        { path: '/training/calendar', label: '训练日历' },
        { path: '/training/fatigue', label: '球员疲劳' },
        { path: '/training/history', label: '训练历史' },
      ],
    },
    ...staticMenuItems.slice(2, 3),
    {
      path: '/leagues',
      label: '联赛',
      icon: Trophy,
      children: [
        { path: myLeagueId ? `/leagues/${myLeagueId}` : '/leagues/all', label: '我的联赛' },
        { path: '/leagues/all', label: '所有联赛' },
      ],
    },
    {
      path: '/cups',
      label: '杯赛',
      icon: Swords,
      children: [
        { path: myCupId ? `/cups/${myCupId}` : '/cups/all', label: '我的杯赛' },
        { path: '/cups/all', label: '所有杯赛' },
      ],
    },
    ...staticMenuItems.slice(3),
  ]

  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {}
    menuItems.forEach((item) => {
      if (item.children) {
        init[item.path] = isInModule(location.pathname, item, menuItems)
      }
    })
    return init
  })

  const toggleExpand = (path: string) => {
    setExpanded((prev) => ({ ...prev, [path]: !prev[path] }))
  }

  const isChildActive = (path: string) => location.pathname === path

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const displayName = user?.nickname || user?.username || 'Manager'
  const firstLetter = displayName.charAt(0).toUpperCase()
  const userLevel = user?.level || 1

  return (
    <aside className="w-60 bg-[#12121A] border-r-2 border-[#2D2D44] flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b-2 border-[#2D2D44]">
        <Link to="/" className="flex items-center gap-2.5 group">
          <img
            src="/logo.png"
            alt="闪电超级联赛"
            className="w-8 h-8 object-cover border-2 border-transparent shadow-glow-green"
          />
          <span className="text-base font-semibold tracking-tight">闪电超级联赛</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 overflow-y-auto">
        <ul className="space-y-1">
          {menuItems.map((item) => {
            const hasChildren = !!item.children
            const isOpen = expanded[item.path]
            const parentActive = isInModule(location.pathname, item, menuItems)

            if (!hasChildren) {
              const active = isSimpleActive(location.pathname, item.path, menuItems)
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={clsx(
                      'flex items-center gap-3 px-4 py-2.5 transition-all duration-200',
                      active
                        ? 'bg-[#0D7377] text-white font-bold border-2 border-[#0A5A5D] shadow-pixel-green'
                        : 'text-[#8B8BA7] hover:text-white hover:bg-[#1E1E2D] border-2 border-transparent',
                    )}
                  >
                    {active && (
                      <span className="text-[#FCD34D] text-xs leading-none">▶</span>
                    )}
                    <item.icon className="w-4 h-4" />
                    <span className="text-sm font-medium">{item.label}</span>
                  </Link>
                </li>
              )
            }

            return (
              <li key={item.path}>
                <button
                  onClick={() => {
                    if (parentActive) {
                      toggleExpand(item.path)
                    } else {
                      setExpanded((prev) => ({ ...prev, [item.path]: true }))
                      navigate(item.path)
                    }
                  }}
                  className={clsx(
                    'w-full flex items-center gap-3 px-4 py-2.5 transition-all duration-200',
                    parentActive
                      ? 'bg-[#0D7377] text-white font-bold border-2 border-[#0A5A5D] shadow-pixel-green'
                      : 'text-[#8B8BA7] hover:text-white hover:bg-[#1E1E2D] border-2 border-transparent',
                  )}
                >
                  {parentActive && (
                    <span className="text-[#FCD34D] text-xs leading-none">▶</span>
                  )}
                  <item.icon className="w-4 h-4" />
                  <span className="text-sm font-medium flex-1 text-left">{item.label}</span>
                  {isOpen ? (
                    <ChevronDown className="w-3 h-3" />
                  ) : (
                    <ChevronRightIcon className="w-3 h-3" />
                  )}
                </button>

                {isOpen && item.children && (
                  <ul className="mt-1 ml-2 space-y-0.5">
                    {item.children.map((child) => (
                      <li key={child.path}>
                        <Link
                          to={child.path}
                          className={clsx(
                            'flex items-center gap-2.5 px-4 py-1.5 text-sm transition-all duration-200 rounded',
                            isChildActive(child.path)
                              ? 'text-white bg-[#1E1E2D]'
                              : 'text-[#6B6B8A] hover:text-[#A0A0B8] hover:bg-[#1E1E2D]/40',
                          )}
                        >
                          <span
                            className={clsx(
                              'w-1 h-1 rounded-full',
                              isChildActive(child.path) ? 'bg-[#0D7377]' : 'bg-[#4B4B6A]',
                            )}
                          />
                          <span className="flex-1">{child.label}</span>
                          {idsLoading && child.label.startsWith('我的') && (
                            <span className="w-2.5 h-2.5 border-2 border-[#4B4B6A] border-t-[#0D7377] rounded-full animate-spin" />
                          )}
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            )
          })}
        </ul>
      </nav>

      {/* User Info */}
      <div className="p-4 border-t-2 border-[#2D2D44]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-[#0D4A4D] border-2 border-[#0D7377]/30 flex items-center justify-center">
            <span className="text-sm font-medium text-white">{firstLetter}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{displayName}</p>
            <p className="text-xs text-[#4B4B6A]">Lv.{userLevel}</p>
          </div>
          <button
            onClick={handleLogout}
            className="p-1.5 text-[#4B4B6A] hover:text-white transition-colors"
            title="退出登录"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}

function isInModule(currentPath: string, item: MenuItem, allItems: MenuItem[]): boolean {
  if (!item.children) {
    return currentPath === item.path
  }
  if (item.children.some((c) => currentPath === c.path)) return true
  if (!currentPath.startsWith(item.path + '/')) return false
  const hijacker = allItems.find(
    (other) =>
      other !== item &&
      !other.children &&
      other.path.startsWith(item.path + '/') &&
      currentPath.startsWith(other.path),
  )
  return !hijacker
}

function isSimpleActive(currentPath: string, path: string, allItems: MenuItem[]): boolean {
  if (path === '/dashboard') return currentPath === '/dashboard'
  const hijacker = allItems.find(
    (other) =>
      other.path !== path &&
      currentPath.startsWith(other.path) &&
      other.path.length > path.length,
  )
  if (hijacker) return false
  return currentPath.startsWith(path)
}

export default Sidebar
