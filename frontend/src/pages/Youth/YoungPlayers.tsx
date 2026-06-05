import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import type { PlayerListItem } from '../../types/player'
import { Card } from '../../components/ui/Card'

const YOUNG_AGE_THRESHOLD = 21

export default function YoungPlayers() {
  const [players, setPlayers] = useState<PlayerListItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function fetch() {
      try {
        const teamRes = await api.get<{ id: string }>('/teams/my-team')
        if (!teamRes.success || !teamRes.data?.id) return
        const playersRes = await api.get<{ items: PlayerListItem[] }>(`/teams/${teamRes.data.id}/players?page_size=100`)
        if (!cancelled && playersRes.success) {
          const all = playersRes.data?.items || []
          const young = all.filter(p => p.age <= YOUNG_AGE_THRESHOLD)
          setPlayers(young)
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

  if (loading) {
    return <div className="max-w-[1400px] p-8 text-center text-[#8B8BA7]">加载中...</div>
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">年轻球员管理</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">球队中 {YOUNG_AGE_THRESHOLD} 岁及以下球员</p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/youth/academy" className="px-3 py-1.5 bg-[#0D7377] border-2 border-[#0A5A5D] text-white text-sm font-medium hover:bg-[#0A5A5D] transition-colors">青训营</Link>
        </div>
      </div>

      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">年轻球员列表</h3>
          <span className="text-xs text-[#4B4B6A]">共 {players.length} 人</span>
        </div>

        {players.length === 0 ? (
          <p className="text-[#8B8BA7] text-center py-8">暂无年轻球员</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b-2 border-[#2D2D44]">
                  <th className="text-left text-xs text-[#4B4B6A] pb-2 font-medium">球员</th>
                  <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">位置</th>
                  <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">年龄</th>
                  <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">OVR</th>
                  <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">潜力</th>
                  <th className="text-right text-xs text-[#4B4B6A] pb-2 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {players.map(p => (
                  <tr key={p.id} className="border-b border-[#2D2D44]/50 hover:bg-[#1E1E2D]/50 transition-colors">
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        {p.avatar_url ? (
                          <img src={`/${p.avatar_url}`} alt={p.name} className="w-8 h-8 object-cover bg-[#1E1E2D]" />
                        ) : (
                          <div className="w-8 h-8 bg-[#1E1E2D] border border-[#2D2D44] flex items-center justify-center">
                            <span className="text-xs font-bold text-[#8B8BA7]">{p.name.charAt(0)}</span>
                          </div>
                        )}
                        <p className="text-sm font-medium text-white">{p.name}</p>
                      </div>
                    </td>
                    <td className="text-center">
                      <span className="text-xs px-2 py-0.5 bg-[#2D2D44] text-white">{p.position}</span>
                    </td>
                    <td className="text-center text-sm text-[#E2E2F0]">{p.age}</td>
                    <td className="text-center text-sm font-bold stat-number">{p.ovr}</td>
                    <td className="text-center">
                      <span className={`text-xs font-bold ${
                        p.potential_letter === 'S' ? 'text-yellow-400' :
                        p.potential_letter === 'A' ? 'text-[#0D7377]' :
                        'text-[#8B8BA7]'
                      }`}>
                        {p.potential_letter}
                      </span>
                    </td>
                    <td className="text-right">
                      <Link to={`/players/${p.id}`} className="text-xs text-[#0D7377] hover:text-white transition-colors">
                        详情 →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
