import { Link, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  Home as LayoutDashboard,
  Users,
  Trophy,
  Calendar as CalendarDays,
  Transfer as ArrowLeftRight,
  Tree as Sprout,
  Sword as Swords,
  Wallet,
  Zap,
  Globe,
  Mailbox,
  Target,
} from '../ui/pixel-icons'

const navItems = [
  { path: '/dashboard', label: '办公室', icon: LayoutDashboard },
  { path: '/team', label: '更衣室', icon: Users },
  { path: '/team/tactics', label: '战术', icon: Target },
  { path: '/match/schedule', label: '赛程', icon: CalendarDays },
  { path: '/training', label: '训练', icon: Zap },
  { path: '/leagues', label: '联赛', icon: Trophy },
  { path: '/cups', label: '杯赛', icon: Swords },
  { path: '/transfer', label: '转会', icon: ArrowLeftRight },
  { path: '/youth', label: '青训', icon: Sprout },
  { path: '/finance', label: '董事会', icon: Wallet },
  { path: '/world', label: '世界', icon: Globe },
]

const secondaryItems = [
  { path: '/mail', label: '收件箱', icon: Mailbox },
]

function TopNav() {
  const location = useLocation()

  const isActive = (path: string) => {
    if (path === '/dashboard') return location.pathname === '/dashboard'
    if (path === '/team') return location.pathname === '/team' || location.pathname.startsWith('/team/players')
    return location.pathname.startsWith(path)
  }

  return (
    <div className="top-nav-bar">
      <nav className="top-nav-main">
        {navItems.map((item) => {
          const active = isActive(item.path)
          return (
            <Link
              key={item.path}
              to={item.path}
              className={clsx(
                'top-nav-link',
                active && 'is-active'
              )}
            >
              <item.icon className="w-3.5 h-3.5" />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>
      <nav className="top-nav-secondary">
        {secondaryItems.map((item) => {
          const active = isActive(item.path)
          return (
            <Link
              key={item.path}
              to={item.path}
              className={clsx(
                'top-nav-link',
                active && 'is-active'
              )}
              title={item.label}
            >
              <item.icon className="w-3.5 h-3.5" />
            </Link>
          )
        })}
      </nav>
    </div>
  )
}

export default TopNav
