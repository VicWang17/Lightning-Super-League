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
  Globe,
  Mailbox,
} from '../ui/pixel-icons'
import { useAuthStore } from '../../stores/auth'

const menuItems = [
  { path: '/dashboard', label: '办公室', icon: LayoutDashboard },
  { path: '/mail', label: '收件箱', icon: Mailbox },
  { path: '/team', label: '更衣室', icon: Users },
  { path: '/match/schedule', label: '赛程表', icon: CalendarDays },
  { path: '/training', label: '训练场', icon: Zap },
  { path: '/leagues', label: '联赛', icon: Trophy },
  { path: '/cups', label: '杯赛', icon: Swords },
  { path: '/transfer', label: '转会市场', icon: ArrowLeftRight },
  { path: '/youth', label: '青训营', icon: Sprout },
  { path: '/finance', label: '董事会', icon: Wallet },
  { path: '/world', label: '世界', icon: Globe },
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
    <aside className="game-sidebar w-60 flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="h-20 flex items-center px-4 border-b-2 border-[#242832] bg-[#07080A]">
        <Link to="/" className="block group">
          <img 
            src="/logo.png" 
            alt="闪电超级联赛" 
            className="h-12 w-auto object-contain"
          />
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-5 px-3 overflow-y-auto">
        <ul className="space-y-2">
          {menuItems.map((item) => (
            <li key={item.path}>
              <Link
                to={item.path}
                className={clsx(
                  'game-nav-link flex items-center gap-3 px-4 py-3 transition-all duration-200 border-2',
                  isActive(item)
                    ? 'is-active bg-[#B8E532] text-[#0A0A0F] font-black border-[#14532D] shadow-pixel-green'
                    : 'text-[#8D947B] bg-[#06070A] hover:text-[#E8EAD8] hover:bg-[#11141A] border-[#1B2028]'
                )}
              >
                {isActive(item) && (
                  <span className="text-[#14532D] text-xs leading-none">▶</span>
                )}
                <item.icon className="w-4 h-4" />
                <span className="text-sm font-bold">{item.label}</span>
              </Link>
            </li>
          ))}
        </ul>
        
        {/* 次级导航 - 查看所有比赛 */}
        <div className="mt-5 pt-5 border-t-2 border-[#242832]">
          <p className="px-4 text-xs text-[#596146] mb-2 font-bold uppercase tracking-wider">赛事入口</p>
          <div className="space-y-1">
            <Link
              to="/leagues/all"
              className={clsx(
                'game-subnav-link flex items-center gap-3 px-4 py-2 text-sm transition-all duration-200 border-2',
                location.pathname === '/leagues' || location.pathname === '/leagues/all'
                  ? 'is-active text-[#B8E532] bg-[#11141A] border-[#242832]'
                  : 'text-[#697157] hover:text-[#C7CBB8] hover:bg-[#11141A] border-transparent'
              )}
            >
              <span className="w-1.5 h-1.5 rounded-none bg-[#B8E532]" />
              联赛
            </Link>
            <Link
              to="/cups/all"
              className={clsx(
                'game-subnav-link flex items-center gap-3 px-4 py-2 text-sm transition-all duration-200 border-2',
                location.pathname === '/cups' || location.pathname === '/cups/all'
                  ? 'is-active text-[#B8E532] bg-[#11141A] border-[#242832]'
                  : 'text-[#697157] hover:text-[#C7CBB8] hover:bg-[#11141A] border-transparent'
              )}
            >
              <span className="w-1.5 h-1.5 rounded-none bg-[#B8E532]" />
              杯赛
            </Link>
          </div>
        </div>
      </nav>

      {/* User Info */}
      <div className="p-4 border-t-2 border-[#242832] bg-[#07080A]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-[#14532D] border-2 border-[#B8E532] flex items-center justify-center">
            <span className="text-sm font-medium text-white">{firstLetter}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-[#E8EAD8] truncate">{displayName}</p>
            <p className="text-xs text-[#697157]">Lv.{userLevel}</p>
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
