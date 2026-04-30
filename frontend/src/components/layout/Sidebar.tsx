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
} from '../ui/pixel-icons'
import { useAuthStore } from '../../stores/auth'

const menuItems = [
  { path: '/dashboard', label: '总览', icon: LayoutDashboard },
  { path: '/team', label: '球队', icon: Users },
  { path: '/match/schedule', label: '赛程', icon: CalendarDays },
  { path: '/training', label: '训练', icon: Zap },
  { path: '/leagues', label: '联赛', icon: Trophy },
  { path: '/cups', label: '杯赛', icon: Swords },
  { path: '/transfer', label: '转会', icon: ArrowLeftRight },
  { path: '/youth', label: '青训', icon: Sprout },
  { path: '/finance', label: '财务', icon: Wallet },
]

function Sidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  
  const isActive = (item: typeof menuItems[0]) => {
    const currentPath = location.pathname
    
    if (item.path === '/dashboard') {
      return currentPath === '/dashboard'
    }
    
    return currentPath.startsWith(item.path)
  }

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
      <div className="h-16 flex items-center px-4 border-b-2 border-[#2D2D44]">
        <Link to="/" className="block group">
          <img 
            src="/logo.png" 
            alt="闪电超级联赛" 
            className="h-12 w-auto object-contain"
          />
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 overflow-y-auto">
        <ul className="space-y-1">
          {menuItems.map((item) => (
            <li key={item.path}>
              <Link
                to={item.path}
                className={clsx(
                  'flex items-center gap-3 px-4 py-2.5 transition-all duration-200',
                  isActive(item)
                    ? 'bg-[#C6F135] text-[#0A0A0F] font-bold border-2 border-[#14532D] shadow-pixel-green'
                    : 'text-[#8B8BA7] hover:text-white hover:bg-[#1E1E2D] border-2 border-transparent'
                )}
              >
                {isActive(item) && (
                  <span className="text-[#14532D] text-xs leading-none">▶</span>
                )}
                <item.icon className="w-4 h-4" />
                <span className="text-sm font-medium">{item.label}</span>
              </Link>
            </li>
          ))}
        </ul>
        
        {/* 次级导航 - 查看所有比赛 */}
        <div className="mt-4 pt-4 border-t-2 border-[#2D2D44]">
          <p className="px-4 text-xs text-[#4B4B6A] mb-2 font-medium uppercase tracking-wider">所有比赛</p>
          <div className="space-y-1">
            <Link
              to="/leagues/all"
              className={clsx(
                'flex items-center gap-3 px-4 py-2 text-sm transition-all duration-200',
                location.pathname === '/leagues' || location.pathname === '/leagues/all'
                  ? 'text-[#C6F135] bg-[#1E1E2D] border-2 border-transparent'
                  : 'text-[#4B4B6A] hover:text-[#8B8BA7] hover:bg-[#1E1E2D]/50 border-2 border-transparent'
              )}
            >
              <span className="w-1.5 h-1.5 rounded-none bg-[#C6F135]" />
              联赛
            </Link>
            <Link
              to="/cups/all"
              className={clsx(
                'flex items-center gap-3 px-4 py-2 text-sm transition-all duration-200',
                location.pathname === '/cups' || location.pathname === '/cups/all'
                  ? 'text-[#C6F135] bg-[#1E1E2D] border-2 border-transparent'
                  : 'text-[#4B4B6A] hover:text-[#8B8BA7] hover:bg-[#1E1E2D]/50 border-2 border-transparent'
              )}
            >
              <span className="w-1.5 h-1.5 rounded-none bg-[#C6F135]" />
              杯赛
            </Link>
          </div>
        </div>
      </nav>

      {/* User Info */}
      <div className="p-4 border-t-2 border-[#2D2D44]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-[#14532D] border-2 border-[#C6F135]/30 flex items-center justify-center">
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

export default Sidebar
