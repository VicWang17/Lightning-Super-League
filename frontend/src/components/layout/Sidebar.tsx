import { Link, useLocation, useNavigate } from 'react-router-dom'
import { clsx } from 'clsx'
import { useState, useEffect } from 'react'
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
import { useAuthStore } from '../../stores/auth'
import api from '../../api/client'

interface Team {
  id: string
  name: string
  current_league_id: string | null
  league_name?: string | null
}

const menuItems = [
  { path: '/dashboard', label: '总览', icon: LayoutDashboard },
  { path: '/team/players', label: '球队', icon: Users },
  { path: '/match/schedule', label: '赛程', icon: CalendarDays },
  { path: '/transfer/market', label: '转会', icon: ArrowLeftRight },
  { path: '/youth', label: '青训', icon: Sprout },
]

function Sidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const [team, setTeam] = useState<Team | null>(null)
  const [isLoadingTeam, setIsLoadingTeam] = useState(false)
  
  useEffect(() => {
    // 获取当前用户的球队信息
    const fetchTeam = async () => {
      setIsLoadingTeam(true)
      try {
        const response = await api.get<Team>('/teams/my-team')
        if (response.success) {
          setTeam(response.data)
        }
      } catch (error) {
        // 用户可能没有球队，这是正常的
        console.log('[Sidebar] 用户没有球队或获取失败')
      } finally {
        setIsLoadingTeam(false)
      }
    }
    
    if (user) {
      fetchTeam()
    }
  }, [user])
  
  // Check if a menu item is active
  const isActive = (item: typeof menuItems[0]) => {
    const currentPath = location.pathname
    
    // Exact match for dashboard
    if (item.path === '/dashboard') {
      return currentPath === '/dashboard'
    }
    
    // Default: check if current path starts with item path
    return currentPath.startsWith(item.path)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  // 获取用户显示名和首字母
  const displayName = user?.nickname || user?.username || 'Manager'
  const firstLetter = displayName.charAt(0).toUpperCase()
  const userLevel = user?.level || 1

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
          
          {/* 联赛菜单项 - 动态指向用户所在联赛 */}
          <li>
            <Link
              to={team?.current_league_id ? `/leagues/${team.current_league_id}` : '/leagues'}
              onClick={() => {
                console.log('[Sidebar] 点击联赛菜单, team=', team, 'current_league_id=', team?.current_league_id)
              }}
              className={clsx(
                'flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200',
                location.pathname.startsWith('/leagues')
                  ? 'bg-[#0D7377] text-white shadow-[0_4px_12px_rgba(13,115,119,0.25)]'
                  : 'text-[#8B8BA7] hover:text-white hover:bg-[#1E1E2D]'
              )}
            >
              <Trophy className="w-4 h-4" />
              <span className="text-sm font-medium">联赛</span>
              {isLoadingTeam && <span className="ml-auto text-xs text-[#4B4B6A]">加载中...</span>}
            </Link>
          </li>
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
