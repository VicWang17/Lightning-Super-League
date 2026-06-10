import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { WarningDiamond, ArrowRight } from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import type { TeamFatigueResponse } from '../../types/training'
import { TrainingPageShell } from './components/TrainingPageShell'

function getRiskColor(risk: string) {
  switch (risk) {
    case 'high': return { border: 'rgba(215,90,74,0.4)', bg: 'rgba(215,90,74,0.12)', text: '#D75A4A' }
    case 'medium': return { border: 'rgba(215,169,74,0.4)', bg: 'rgba(215,169,74,0.12)', text: '#D7A94A' }
    default: return { border: 'rgba(16,185,129,0.4)', bg: 'rgba(16,185,129,0.12)', text: '#9ECF45' }
  }
}

function getRiskLabel(risk: string) {
  switch (risk) {
    case 'high': return '高风险'
    case 'medium': return '中等'
    default: return '正常'
  }
}

function getFatigueBarColor(v: number) {
  if (v >= 80) return '#D75A4A'
  if (v >= 60) return '#D7A94A'
  return '#9ECF45'
}

function getRiskFromFatigue(fatigue: number): 'high' | 'medium' | 'low' {
  if (fatigue >= 75) return 'high'
  if (fatigue >= 50) return 'medium'
  return 'low'
}

export default function PlayerFatigue() {
  const navigate = useNavigate()
  const [data, setData] = useState<TeamFatigueResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<'fatigue' | 'risk'>('fatigue')

  useEffect(() => {
    let cancelled = false
    async function fetch() {
      try {
        const teamRes = await api.get<{ id: string }>('/teams/my-team')
        if (!teamRes.success || !teamRes.data?.id) return
        const fatigueRes = await api.getTeamFatigue(teamRes.data.id)
        if (!cancelled && fatigueRes.success) {
          setData(fatigueRes.data)
        }
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetch()
    return () => { cancelled = true }
  }, [])

  const sorted = useMemo(() => {
    if (!data?.players) return []
    const arr = [...data.players]
    if (sortBy === 'fatigue') {
      arr.sort((a, b) => b.fatigue - a.fatigue)
    } else {
      const riskOrder = { high: 0, medium: 1, low: 2 }
      arr.sort((a, b) => riskOrder[getRiskFromFatigue(a.fatigue)] - riskOrder[getRiskFromFatigue(b.fatigue)])
    }
    return arr
  }, [data, sortBy])

  const highRiskCount = useMemo(() => data?.players?.filter(p => getRiskFromFatigue(p.fatigue) === 'high').length ?? 0, [data])
  const avgFatigue = useMemo(() => data?.avg_fatigue ?? 0, [data])
  const totalPlayers = data?.players?.length ?? 0
  const goodCount = data?.players?.filter(p => p.fatigue <= 60).length ?? 0

  if (loading) {
    return (
      <TrainingPageShell title="球员疲劳" subtitle="监控全队疲劳状态，预防伤病">
        <div className="training-panel" style={{ padding: 36, textAlign: 'center', color: 'var(--tr-muted)', fontWeight: 900 }}>
          加载中…
        </div>
      </TrainingPageShell>
    )
  }

  return (
    <TrainingPageShell
      title="球员疲劳"
      subtitle="监控全队疲劳状态，预防伤病"
      actionBar={
        <button onClick={() => navigate('/training/weekly')} className="training-ghost-btn">
          去周计划调整 <ArrowRight className="h-4 w-4" />
        </button>
      }
    >
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 10, marginBottom: 16 }}>
        <div className="training-stat-tile is-amber">
          <span>平均疲劳</span>
          <strong style={{ color: avgFatigue > 60 ? '#D7A94A' : undefined }}>{avgFatigue.toFixed(0)}%</strong>
        </div>
        <div className="training-stat-tile is-red">
          <span>高风险球员</span>
          <strong style={{ color: highRiskCount > 0 ? '#D75A4A' : undefined }}>{highRiskCount} 人</strong>
        </div>
        <div className="training-stat-tile is-blue">
          <span>总球员数</span>
          <strong>{totalPlayers} 人</strong>
        </div>
        <div className="training-stat-tile is-green">
          <span>状态良好</span>
          <strong>{goodCount} 人</strong>
        </div>
      </div>

      {highRiskCount > 0 && (
        <div className="training-panel tone-red" style={{ padding: 16, marginBottom: 16, borderColor: 'rgba(215,90,74,0.4)' }}>
          <h3 style={{ color: '#D75A4A', fontSize: 18, fontWeight: 1000, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <WarningDiamond className="h-4 w-4" />
            需要立即休息的球员
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10 }}>
            {sorted
              .filter(p => getRiskFromFatigue(p.fatigue) === 'high')
              .map(p => {
                const rc = getRiskColor('high')
                return (
                  <div
                    key={p.player_id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      padding: 12,
                      background: rc.bg,
                      border: `2px solid ${rc.border}`,
                    }}
                  >
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: 'rgba(215,90,74,0.15)',
                        border: '2px solid rgba(215,90,74,0.35)',
                        fontSize: 14,
                        fontWeight: 1000,
                        color: '#D75A4A',
                      }}
                    >
                      {p.player_name.charAt(0)}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ color: 'var(--tr-text)', fontSize: 13, fontWeight: 800, margin: 0 }}>{p.player_name}</p>
                      <p style={{ color: 'var(--tr-muted)', fontSize: 11, fontWeight: 800, margin: '2px 0 0' }}>{p.recommendation}</p>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <p style={{ color: '#D75A4A', fontSize: 16, fontWeight: 1000, margin: 0 }}>{p.fatigue}%</p>
                      <p style={{ color: 'rgba(215,90,74,0.7)', fontSize: 10, fontWeight: 800, margin: '2px 0 0' }}>疲劳值</p>
                    </div>
                  </div>
                )
              })}
          </div>
        </div>
      )}

      <div className="training-panel" style={{ padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <h3 style={{ color: 'var(--tr-text)', fontSize: 18, fontWeight: 1000, margin: 0 }}>全队疲劳详情</h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => setSortBy('fatigue')}
              className={`training-ghost-btn ${sortBy === 'fatigue' ? 'is-active' : ''}`}
              style={sortBy === 'fatigue' ? { borderColor: 'var(--tr-accent)', color: 'var(--tr-accent)' } : {}}
            >
              按疲劳排序
            </button>
            <button
              onClick={() => setSortBy('risk')}
              className={`training-ghost-btn ${sortBy === 'risk' ? 'is-active' : ''}`}
              style={sortBy === 'risk' ? { borderColor: 'var(--tr-accent)', color: 'var(--tr-accent)' } : {}}
            >
              按风险排序
            </button>
          </div>
        </div>

        <div style={{ display: 'grid', gap: 8 }}>
          {sorted.map(p => {
            const risk = getRiskFromFatigue(p.fatigue)
            const rc = getRiskColor(risk)
            return (
              <div
                key={p.player_id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '40px 100px 1fr 40px 60px',
                  gap: 12,
                  alignItems: 'center',
                  padding: 12,
                  background: 'rgba(5,6,9,0.86)',
                  border: '2px solid var(--tr-border)',
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'rgba(255,255,255,0.04)',
                    border: '2px solid var(--tr-border)',
                    fontSize: 14,
                    fontWeight: 1000,
                    color: 'var(--tr-text)',
                  }}
                >
                  {p.player_name.charAt(0)}
                </div>
                <div style={{ minWidth: 0 }}>
                  <p style={{ color: 'var(--tr-text)', fontSize: 13, fontWeight: 800, margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {p.player_name}
                  </p>
                  <p style={{ color: 'var(--tr-muted)', fontSize: 11, fontWeight: 800, margin: '2px 0 0' }}>
                    {p.recommendation}
                  </p>
                </div>
                <div className="pixel-progress-track" style={{ height: 10 }}>
                  <div
                    className="pixel-progress-fill"
                    style={{ height: '100%', background: getFatigueBarColor(p.fatigue), width: `${Math.min(100, p.fatigue)}%` }}
                  />
                </div>
                <span style={{ color: p.fatigue > 60 ? '#D7A94A' : '#9ECF45', fontSize: 13, fontWeight: 1000, textAlign: 'right', fontFamily: 'Roboto Mono, monospace' }}>
                  {p.fatigue}%
                </span>
                <span
                  style={{
                    display: 'inline-block',
                    fontSize: 11,
                    fontWeight: 1000,
                    padding: '3px 6px',
                    border: `2px solid ${rc.border}`,
                    background: rc.bg,
                    color: rc.text,
                    textAlign: 'center',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {getRiskLabel(risk)}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </TrainingPageShell>
  )
}
