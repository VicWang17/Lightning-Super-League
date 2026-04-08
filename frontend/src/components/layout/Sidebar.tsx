import { Link, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import { 
  LayoutDashboard, 
  Users, 
  Trophy, 
  CalendarDays, 
  ArrowLeftRight, 
  Sprout,
  Zap,
  LogOut
} from 'lucide-react'

const menuItems = [
  { path: '/dashboard', label: '总览', icon: LayoutDashboard },
  { path: '/team', label: '球队', icon: Users },
  { path: '/league', label: '联赛', icon: Trophy },
  { path: '/schedule', label: '赛程', icon: CalendarDays },
  { path: '/transfer', label: '转会', icon: ArrowLeftRight },
  { path: '/youth', label: '青训', icon: Sprout },
]

function Sidebar() {
  const location = useLocation()

  return (
    <aside className="w-60 bg-[#12121A] border-r border-[#2D2D44] flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-[#2D2D44]">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-[#0D7377] flex items-center justify-center shadow-[0_0_12px_rgba(13,115,119,0.4)]">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="text-base font-semibold tracking-tight">闪电超级联赛</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3">
        <ul className="space-y-1">
          {menuItems.map((item) => (
            <li key={item.path}>
              <Link
                to={item.path}
                className={clsx(
                  'flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200',
                  location.pathname === item.path
                    ? 'bg-[#0D7377] text-white shadow-[0_4px_12px_rgba(13,115,119,0.25)]'
                    : 'text-[#8B8BA7] hover:text-white hover:bg-[#1E1E2D]'
                )}
              >
                <item.icon className="w-4 h-4" />
                <span className="text-sm font-medium">{item.label}</span>
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      {/* User Info */}
      <div className="p-4 border-t border-[#2D2D44]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-[#0D4A4D] border border-[#0D7377]/30 flex items-center justify-center">
            <span className="text-sm font-medium text-white">M</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">Manager</p>
            <p className="text-xs text-[#4B4B6A]">Lv.12</p>
          </div>
          <button className="p-1.5 text-[#4B4B6A] hover:text-white transition-colors">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
