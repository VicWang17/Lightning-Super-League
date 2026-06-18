import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, User } from '../../components/ui/pixel-icons'
import { FatigueStatus } from '../../components/ui/FatigueStatus'
import Avatar from '../../components/ui/Avatar'
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

function getRiskFromFatigue(fatigue: number): 'high' | 'medium' | 'low' {
  if (fatigue >= 75) return 'high'
  if (fatigue >= 50) return 'medium'
  return 'low'
}

export default function PlayerFatigue() {
  const navigate = useNavigate()
  const [data, setData] = useState<TeamFatigueResponse | null>(null)
  const [loading, setLoading] = useState(true)

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

  const players = useMemo(() => {
    if (!data?.players) return []
    return [...data.players].sort((a, b) => b.fatigue - a.fatigue)
  }, [data])

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
          <strong style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, color: avgFatigue > 60 ? '#D7A94A' : undefined }}>
            <FatigueStatus fatigue={avgFatigue} size={20} />
          </strong>
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

      <div className="training-panel" style={{ padding: 16, marginTop: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <h3 style={{ color: 'var(--tr-text)', fontSize: 18, fontWeight: 1000, margin: 0 }}>全队疲劳详情</h3>
        </div>

        <div style={{ display: 'grid', gap: 8 }}>
          {players.map(p => {
            const risk = getRiskFromFatigue(p.fatigue)
            const rc = getRiskColor(risk)
            return (
              <div
                key={p.player_id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '40px 1fr 40px 70px',
                  gap: 12,
                  alignItems: 'center',
                  padding: 12,
                  background: 'rgba(5,6,9,0.86)',
                  border: '2px solid var(--tr-border)',
                }}
              >
                <Avatar
                  src={p.avatar_url ? `/${p.avatar_url}` : undefined}
                  name={p.player_name}
                  size="md"
                  fallback={<User className="w-5 h-5 text-[#8B8BA7]" />}
                />
                <div style={{ minWidth: 0 }}>
                  <p style={{ color: 'var(--tr-text)', fontSize: 13, fontWeight: 800, margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {p.player_name}
                  </p>
                  <p style={{ color: 'var(--tr-muted)', fontSize: 11, fontWeight: 800, margin: '2px 0 0' }}>
                    {p.recommendation}
                  </p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <FatigueStatus fatigue={p.fatigue} size={22} />
                </div>
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
