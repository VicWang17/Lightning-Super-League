import { useEffect, useState } from 'react'
import { Bell, SettingsCog as Settings, Trophy, Calendar, Clock } from '../ui/pixel-icons'
import { useSeason } from '../../hooks/useSeason'
import { useGameClock } from '../../hooks/useGameClock'

function Header() {
  const { displayStatus, loading, error, season } = useSeason()
  const { virtualNow, mode, speed, error: clockError } = useGameClock()
  const [skin, setSkin] = useState<'green' | 'blue'>(() => {
    if (typeof window === 'undefined') return 'green'
    return localStorage.getItem('game-skin') === 'blue' ? 'blue' : 'green'
  })

  useEffect(() => {
    document.documentElement.dataset.skin = skin
    localStorage.setItem('game-skin', skin)
  }, [skin])

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
    <header className="game-header h-20 flex items-center justify-between px-6 sticky top-0 z-40">
      <div className="flex items-center gap-4">
        <div className="game-hud-panel px-4 py-2">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#7F8A63]">Manager Office</p>
          <p className="text-sm font-black text-[#E8EAD8]">俱乐部中枢</p>
        </div>
      </div>
      
      {/* Right */}
      <div className="flex items-center gap-4">
        {/* Game Clock */}
        <div className="flex items-center gap-3">
          <div className={`game-icon-box w-10 h-10 flex items-center justify-center border-2 ${
            mode === 'paused'
              ? 'bg-[#3B270D] border-[#D4A017]'
            : mode === 'turbo'
              ? 'bg-[#123D32] border-[#9ECF45]'
              : mode === 'step'
              ? 'bg-[#241B3A] border-[#8A2BE2]'
              : 'bg-[#07080A] border-[#242832]'
          }`}>
            <Clock className={`w-5 h-5 ${
              mode === 'paused'
                ? 'text-[#D4A017]'
                : mode === 'turbo'
                ? 'text-[#9ECF45]'
                : mode === 'step'
                ? 'text-[#8A2BE2]'
                : 'text-[#9CA77A]'
            }`} />
          </div>
          <div className="text-right">
            <p className="text-xs text-[#697157] uppercase tracking-wider">
              {clockError ? '时钟同步失败' : `${mode}${mode === 'turbo' ? ` ×${speed}` : ''}`}
            </p>
            <p className="text-sm font-bold text-[#E8EAD8] font-mono">
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
        <div className="w-px h-8 bg-[#242832]" />

        {/* Season Info */}
        <div className="flex items-center gap-3">
          <div className={`game-icon-box w-10 h-10 flex items-center justify-center ${
            hasMatchesToday 
              ? 'bg-[#0C1A0D] border-2 border-[#9ECF45]' 
              : 'bg-[#07080A] border-2 border-[#242832]'
          }`}>
            {hasMatchesToday ? (
              <Calendar className="w-5 h-5 text-[#B8E532]" />
            ) : (
              <Trophy className="w-5 h-5 text-[#9CA77A]" />
            )}
          </div>
          <div className="text-right">
            <p className="text-xs text-[#697157] uppercase tracking-wider">
              {displayStatus?.has_league && `联赛第${displayStatus.league_round}轮`}
              {displayStatus?.has_league && displayStatus?.has_cup && ' · '}
              {displayStatus?.has_cup && '杯赛日'}
              {!displayStatus?.has_league && !displayStatus?.has_cup && '今日无比赛'}
            </p>
            <p className="text-sm font-bold text-[#E8EAD8]">{seasonDisplay}</p>
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
            <p className="text-[10px] text-[#697157] mt-1 text-right">
              {displayStatus.progress_percent}%
            </p>
          </div>
        )}

        {/* Divider */}
        <div className="w-px h-8 bg-[#242832]" />

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSkin(skin === 'green' ? 'blue' : 'green')}
            className="skin-toggle h-9 px-3 border-2 flex items-center justify-center text-xs font-black transition-colors hover:-translate-x-0.5 hover:-translate-y-0.5"
            title="切换黑绿/黑蓝皮肤"
          >
            {skin === 'green' ? 'BLUE' : 'GREEN'}
          </button>
          <button className="game-action-btn w-9 h-9 border-2 flex items-center justify-center transition-colors hover:-translate-x-0.5 hover:-translate-y-0.5">
            <Bell className="w-4 h-4" />
          </button>
          <button className="game-action-btn w-9 h-9 border-2 flex items-center justify-center transition-colors hover:-translate-x-0.5 hover:-translate-y-0.5">
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  )
}

export default Header
