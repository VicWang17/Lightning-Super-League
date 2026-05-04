import { Bell, SettingsCog as Settings, Search, Trophy, Calendar, Clock } from '../ui/pixel-icons'
import { useSeason } from '../../hooks/useSeason'
import { useGameClock } from '../../hooks/useGameClock'

function Header() {
  const { displayStatus, loading, error, season } = useSeason()
  const { virtualNow, mode, speed, error: clockError } = useGameClock()

  // 调试信息
  console.log('Header render:', { loading, error, hasSeason: !!season, hasDisplayStatus: !!displayStatus })

  // 生成显示文本
  let seasonDisplay: string
  if (loading) {
    seasonDisplay = '加载中...'
  } else if (error) {
    seasonDisplay = `赛季信息不可用 (${error})`
  } else if (displayStatus?.display_text) {
    seasonDisplay = displayStatus.display_text
  } else if (season) {
    seasonDisplay = `第${season.season_number}赛季 第${season.current_day}/${season.total_days}天`
  } else {
    seasonDisplay = '赛季信息不可用'
  }

  // 判断是否有今日比赛
  const hasMatchesToday = displayStatus && displayStatus.total_fixtures_today > 0

  return (
    <header className="h-16 bg-[#0A0A0F]/80 border-b-2 border-[#2D2D44] flex items-center justify-between px-6 sticky top-0 z-40">
      {/* Left - Search */}
      <div className="flex items-center gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#4B4B6A]" />
          <input 
            type="text" 
            placeholder="搜索球员、球队..."
            className="w-64 bg-[#12121A] border-2 border-[#2D2D44] pl-10 pr-4 py-2 text-sm text-[#E2E2F0] placeholder:text-[#4B4B6A] focus:outline-none focus:border-[#0D7377]/50 transition-colors"
          />
        </div>
      </div>
      
      {/* Right */}
      <div className="flex items-center gap-6">
        {/* Game Clock */}
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 flex items-center justify-center border-2 ${
            mode === 'paused'
              ? 'bg-[#8B4513]/20 border-[#D4A017]/50'
              : mode === 'turbo'
              ? 'bg-[#0D7377]/20 border-[#0D7377]/50'
              : mode === 'step'
              ? 'bg-[#4B0082]/20 border-[#8A2BE2]/50'
              : 'bg-[#12121A] border-[#2D2D44]'
          }`}>
            <Clock className={`w-5 h-5 ${
              mode === 'paused'
                ? 'text-[#D4A017]'
                : mode === 'turbo'
                ? 'text-[#0D7377]'
                : mode === 'step'
                ? 'text-[#8A2BE2]'
                : 'text-[#8B8BA7]'
            }`} />
          </div>
          <div className="text-right">
            <p className="text-xs text-[#4B4B6A] uppercase tracking-wider">
              {clockError ? '时钟同步失败' : `${mode}${mode === 'turbo' ? ` ×${speed}` : ''}`}
            </p>
            <p className="text-sm font-medium text-[#E2E2F0] font-mono">
              {virtualNow.toLocaleDateString('zh-CN', {
                month: '2-digit',
                day: '2-digit',
              })} {' '}
              {virtualNow.toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false,
              })}
            </p>
          </div>
        </div>

        {/* Divider */}
        <div className="w-px h-8 bg-[#2D2D44]" />

        {/* Season Info */}
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 flex items-center justify-center ${
            hasMatchesToday 
              ? 'bg-[#0D7377]/20 border-2 border-[#0D7377]/50' 
              : 'bg-[#12121A] border-2 border-[#2D2D44]'
          }`}>
            {hasMatchesToday ? (
              <Calendar className="w-5 h-5 text-[#0D7377]" />
            ) : (
              <Trophy className="w-5 h-5 text-[#8B8BA7]" />
            )}
          </div>
          <div className="text-right">
            <p className="text-xs text-[#4B4B6A] uppercase tracking-wider">
              {displayStatus?.has_league && `联赛第${displayStatus.league_round}轮`}
              {displayStatus?.has_league && displayStatus?.has_cup && ' · '}
              {displayStatus?.has_cup && '杯赛日'}
              {!displayStatus?.has_league && !displayStatus?.has_cup && '今日无比赛'}
            </p>
            <p className="text-sm font-medium text-[#E2E2F0]">{seasonDisplay}</p>
          </div>
        </div>

        {/* Progress Bar (mini) */}
        {displayStatus && (
          <div className="w-24">
            <div className="pixel-progress-track h-2">
              <div 
                className="pixel-progress-fill transition-all duration-500"
                style={{ width: `${displayStatus.progress_percent}%` }}
              />
            </div>
            <p className="text-[10px] text-[#4B4B6A] mt-1 text-right">
              {displayStatus.progress_percent}%
            </p>
          </div>
        )}

        {/* Divider */}
        <div className="w-px h-8 bg-[#2D2D44]" />

        {/* Funds */}
        <div className="text-right">
          <p className="text-xs text-[#4B4B6A]">球队资金</p>
          <p className="text-lg font-semibold stat-number text-white">€ 10.5M</p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button className="w-9 h-9 bg-[#12121A] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 flex items-center justify-center text-[#8B8BA7] hover:text-white transition-colors hover:-translate-x-0.5 hover:-translate-y-0.5">
            <Bell className="w-4 h-4" />
          </button>
          <button className="w-9 h-9 bg-[#12121A] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 flex items-center justify-center text-[#8B8BA7] hover:text-white transition-colors hover:-translate-x-0.5 hover:-translate-y-0.5">
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  )
}

export default Header
