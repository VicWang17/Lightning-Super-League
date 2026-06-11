import { useState } from 'react'
import { Bell, SettingsCog as Settings, Clock, ChevronDown } from '../ui/pixel-icons'
import { useSeason } from '../../hooks/useSeason'
import { useGameClock } from '../../hooks/useGameClock'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../../stores/auth'

function Header() {
  const { displayStatus, loading, error, season } = useSeason()
  const { mode } = useGameClock()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  const [showUserMenu, setShowUserMenu] = useState(false)

  const modeColor = {
    paused: 'text-amber-400',
    turbo: 'text-[#9ECF45]',
    step: 'text-purple-400',
    normal: 'text-[#697157]',
  } as Record<string, string>

  let seasonDisplay: string
  if (loading) {
    seasonDisplay = '加载中...'
  } else if (error) {
    seasonDisplay = '赛季信息不可用'
  } else if (displayStatus?.display_text) {
    seasonDisplay = displayStatus.display_text
  } else if (season) {
    seasonDisplay = `第${season.season_number}赛季 第${season.current_day}天`
  } else {
    seasonDisplay = '赛季信息不可用'
  }

  const hasMatchesToday = displayStatus && displayStatus.total_fixtures_today > 0

  const displayName = user?.nickname || user?.username || 'Manager'
  const firstLetter = displayName.charAt(0).toUpperCase()

  return (
    <header className="game-command-bar">
      {/* Left: Team Identity */}
      <div className="flex items-center gap-3">
        <Link to="/team" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-full bg-[#14532D] border border-[#B8E532] flex items-center justify-center shrink-0">
            <span className="text-xs font-bold text-white">{firstLetter}</span>
          </div>
          <div className="leading-none">
            <p className="text-sm font-black text-[#E8EAD8] group-hover:text-[#B8E532] transition-colors">
              {displayName}
            </p>
          </div>
        </Link>
      </div>

      {/* Center: Season & Match Info */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5 text-xs">
          <Clock className={`w-3.5 h-3.5 ${modeColor[mode] || modeColor.normal}`} />
          <span className="text-[#697157]">{seasonDisplay}</span>
        </div>

        {displayStatus && (
          <div className="w-20 hidden sm:block">
            <div className="h-1.5 bg-[#0A0A0F] border border-[#242832]">
              <div
                className="h-full bg-[#B8E532]"
                style={{ width: `${displayStatus.progress_percent}%` }}
              />
            </div>
          </div>
        )}

        {hasMatchesToday && (
          <Link
            to="/match/schedule"
            className="flex items-center gap-1.5 px-2 py-0.5 bg-[#0C1A0D] border border-[#9ECF45]/30 text-[10px] text-[#9ECF45] font-bold hover:bg-[#9ECF45]/10 transition-colors"
          >
            <span>今日比赛</span>
          </Link>
        )}
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        <button className="command-btn" title="通知">
          <Bell className="w-4 h-4" />
        </button>
        <button className="command-btn" title="设置">
          <Settings className="w-4 h-4" />
        </button>

        <div className="w-px h-5 bg-[#242832] mx-1" />

        <button
          className="flex items-center gap-1.5 px-2 py-1 hover:bg-[#11141A] transition-colors"
          onClick={() => setShowUserMenu(!showUserMenu)}
        >
          <div className="w-6 h-6 bg-[#1B2028] border border-[#2D2D44] flex items-center justify-center">
            <span className="text-[10px] font-bold text-[#8D947B]">{firstLetter}</span>
          </div>
          <ChevronDown className="w-3 h-3 text-[#4B4B6A]" />
        </button>

        {showUserMenu && (
          <div className="absolute right-4 top-12 bg-[#0A0A0F] border border-[#2D2D44] shadow-xl z-50 min-w-[140px]">
            <button
              onClick={() => {
                logout()
                navigate('/login')
              }}
              className="w-full text-left px-3 py-2 text-xs text-[#8D947B] hover:text-white hover:bg-[#1E1E2D] transition-colors"
            >
              退出登录
            </button>
          </div>
        )}
      </div>
    </header>
  )
}

export default Header
