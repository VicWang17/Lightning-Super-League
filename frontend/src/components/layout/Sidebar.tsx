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

// 当前用户的球队所在的联赛ID（东区超级联赛 - 第一个联赛）
// 实际应用中应该从用户状态或API获取
const USER_TEAM_LEAGUE_ID = 'f1efeae9-f824-4a6d-a2a7-d9ce5791b785'

const menuItems = [
  { path: '/dashboard', label: '总览', icon: LayoutDashboard },
  { path: '/team/players', label: '球队', icon: Users },
  { 
    path: `/leagues/${USER_TEAM_LEAGUE_ID}`, // 指向用户球队所在的联赛
    label: '联赛', 
    icon: Trophy,
    matchPaths: ['/leagues'] // 匹配所有联赛相关路径
  },
  { path: '/match/schedule', label: '赛程', icon: CalendarDays },
  { path: '/transfer/market', label: '转会', icon: ArrowLeftRight },
  { path: '/youth', label: '青训', icon: Sprout },
]

function Sidebar() {
  const location = useLocation()
  
  // Check if a menu item is active
  const isActive = (item: typeof menuItems[0]) => {
    const currentPath = location.pathname
    
    // Exact match for dashboard
    if (item.path === '/dashboard') {
      return currentPath === '/dashboard'
    }
    
    // For items with matchPaths, check if current path starts with any of them
    if ('matchPaths' in item && item.matchPaths) {
      return item.matchPaths.some(path => currentPath.startsWith(path))
    }
    
    // Default: check if current path starts with item path
    return currentPath.startsWith(item.path)
  }

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
                  isActive(item)
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
        
        {/* 次级导航 - 查看所有联赛 */}
        <div className="mt-4 pt-4 border-t border-[#2D2D44]">
          <Link
            to="/leagues"
            className={clsx(
              'flex items-center gap-3 px-4 py-2 rounded-lg text-sm transition-all duration-200',
              location.pathname === '/leagues'
                ? 'text-white bg-[#1E1E2D]'
                : 'text-[#4B4B6A] hover:text-[#8B8BA7] hover:bg-[#1E1E2D]/50'
            )}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#4B4B6A]" />
            所有联赛
          </Link>
        </div>
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
