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
    paused: 'text-[#C77A00]',
    turbo: 'text-[#B9EF3F]',
    step: 'text-[#C77A00]',
    normal: 'text-[#466353]',
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
  const seasonProgress = displayStatus
    ? Math.min(100, Math.max(0, displayStatus.progress_percent || 0))
    : 0

  const displayName = user?.nickname || user?.username || 'Manager'
  const firstLetter = displayName.charAt(0).toUpperCase()

  return (
    <header className="game-command-bar fresh-command-bar">
      <div className="command-bar-inner fresh-command-inner">
        <Link to="/team" className="command-club-link fresh-club-link group">
          <div className="command-club-avatar fresh-club-avatar">
            <span>{firstLetter}</span>
          </div>
          <div className="command-club-meta fresh-club-meta">
            <span>经理席</span>
            <strong>
              {displayName}
            </strong>
          </div>
        </Link>

        <div className="command-season-panel fresh-season-panel">
          <div className="command-season-clock fresh-season-clock">
            <Clock className={modeColor[mode] || modeColor.normal} />
            <span>{seasonDisplay}</span>
          </div>
          {displayStatus && (
            <div className="command-season-progress fresh-season-progress" aria-hidden="true">
              <div
                className="command-season-progress-fill fresh-season-progress-fill"
                style={{ width: `${seasonProgress}%` }}
              />
            </div>
          )}

          {hasMatchesToday && (
            <Link to="/match/schedule" className="command-match-btn fresh-match-btn">
              今日 {displayStatus.total_fixtures_today} 场
            </Link>
          )}
        </div>

        <div className="command-actions fresh-command-actions">
          <button className="command-btn fresh-command-btn" title="通知">
            <Bell className="w-4 h-4" />
          </button>
          <button className="command-btn fresh-command-btn" title="设置">
            <Settings className="w-4 h-4" />
          </button>

          <div className="command-action-separator fresh-action-separator" />

          <button
            className="command-user-btn fresh-user-btn"
            onClick={() => setShowUserMenu(!showUserMenu)}
          >
            <span>{firstLetter}</span>
            <ChevronDown className="w-3 h-3" />
          </button>

          {showUserMenu && (
            <div className="command-user-menu">
              <button
                onClick={() => {
                  logout()
                  navigate('/login')
                }}
              >
                退出登录
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default Header
