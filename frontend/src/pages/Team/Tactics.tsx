import { useEffect, useState } from 'react'
import {
  Sword,
  Target,
  Download
} from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import type { PlayerListItem } from '../../types/player'
import { Card } from '../../components/ui/Card'

// 阵型定义（前端游戏常量）
const formations = [
  { id: '1-2-3', name: '1-2-3', label: '进攻型', desc: '1门将 + 2后卫 + 3前锋', attack: 85, defense: 45, control: 50 },
  { id: '1-3-2', name: '1-3-2', label: '均衡型', desc: '1门将 + 3中场 + 2前锋', attack: 60, defense: 60, control: 70 },
  { id: '2-1-3', name: '2-1-3', label: '控球型', desc: '2后卫 + 1后腰 + 3前锋', attack: 70, defense: 50, control: 80 },
  { id: '2-3-1', name: '2-3-1', label: '防守反击', desc: '2后卫 + 3中场 + 1前锋', attack: 45, defense: 80, control: 60 },
  { id: '1-1-4', name: '1-1-4', label: '全攻型', desc: '1门将 + 1后卫 + 4前锋', attack: 95, defense: 30, control: 40 },
]

// 战术心态（前端游戏常量）
const mentalities = [
  { id: 'ultra-attacking', name: '全力进攻', desc: '高风险高回报', color: 'text-red-400' },
  { id: 'attacking', name: '积极进攻', desc: '主动压迫', color: 'text-orange-400' },
  { id: 'balanced', name: '攻守平衡', desc: '标准打法', color: 'text-[#0D7377]' },
  { id: 'defensive', name: '稳守反击', desc: '收缩防线', color: 'text-blue-400' },
  { id: 'ultra-defensive', name: '死守', desc: '铁桶阵', color: 'text-[#4B4B6A]' },
]

const positionColors: Record<string, string> = {
  GK: 'bg-amber-500',
  DF: 'bg-blue-500',
  MF: 'bg-emerald-500',
  FW: 'bg-red-500',
}

// 根据球员位置简单映射坐标（七人制球场）
function getPositionCoords(position: string, index: number, total: number) {
  const pos = position as string
  if (pos === 'GK') return { x: 50, y: 88 }
  if (pos === 'DF' || pos === 'CB') {
    const count = total
    const spacing = count > 1 ? 60 / (count - 1) : 0
    return { x: 20 + spacing * index, y: 65 }
  }
  if (pos === 'MF' || pos === 'CMF' || pos === 'DMF' || pos === 'AMF') {
    return { x: 30 + (index % 3) * 20, y: 48 }
  }
  if (pos === 'FW' || pos === 'ST' || pos === 'WF') {
    return { x: 25 + (index % 3) * 25, y: 22 }
  }
  return { x: 20 + Math.random() * 60, y: 50 }
}

export default function Tactics() {
  const [players, setPlayers] = useState<PlayerListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedFormation, setSelectedFormation] = useState(formations[1])
  const [selectedMentality, setSelectedMentality] = useState(mentalities[2])
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function fetch() {
      try {
        const teamRes = await api.get<{ id: string }>('/teams/my-team')
        if (!teamRes.success || !teamRes.data?.id) return
        const playersRes = await api.get<{ items: PlayerListItem[] }>(`/teams/${teamRes.data.id}/players?page_size=100`)
        if (!cancelled && playersRes.success) {
          // 取 OVR 最高的 7 人作为首发
          const sorted = (playersRes.data?.items || []).sort((a, b) => b.ovr - a.ovr)
          setPlayers(sorted.slice(0, 7))
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

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  if (loading) {
    return <div className="max-w-[1400px] p-8 text-center text-[#8B8BA7]">加载中...</div>
  }

  // 按位置分组计算坐标
  const posCounts: Record<string, number> = {}
  const posIndices: Record<string, number> = {}
  for (const p of players) {
    const group = p.position === 'GK' ? 'GK' : p.position === 'DF' ? 'DF' : p.position === 'MF' ? 'MF' : 'FW'
    posCounts[group] = (posCounts[group] || 0) + 1
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">战术设置</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">配置阵型、心态与战术指令</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-4 py-2 bg-[#0D7377] border-2 border-[#0A5A5D] text-white text-sm font-medium hover:bg-[#0A5A5D] transition-all"
          >
            <Download className="w-4 h-4" />
            {saved ? '已保存!' : '保存战术'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧 - 阵型选择 */}
        <div className="space-y-6">
          <Card>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Target className="w-4 h-4 text-[#0D7377]" />
              阵型选择
            </h3>
            <div className="space-y-2">
              {formations.map(f => (
                <button
                  key={f.id}
                  onClick={() => setSelectedFormation(f)}
                  className={`w-full text-left p-3 border-2 transition-all duration-200 ${
                    selectedFormation.id === f.id
                      ? 'bg-[#0D7377]/20 border-[#0D7377] shadow-pixel-green'
                      : 'bg-[#0A0A0F] border-[#2D2D44] hover:border-[#0D7377]/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-bold text-white">{f.name}</p>
                      <p className="text-xs text-[#8B8BA7]">{f.desc}</p>
                    </div>
                    <span className={`text-xs px-2 py-0.5 border ${
                      f.label === '进攻型' || f.label === '全攻型' ? 'text-red-400 border-red-400/30' :
                      f.label === '防守反击' || f.label === '防守型' ? 'text-blue-400 border-blue-400/30' :
                      'text-[#0D7377] border-[#0D7377]/30'
                    }`}>
                      {f.label}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </Card>

          <Card>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Sword className="w-4 h-4 text-[#0D7377]" />
              比赛心态
            </h3>
            <div className="space-y-2">
              {mentalities.map(m => (
                <button
                  key={m.id}
                  onClick={() => setSelectedMentality(m)}
                  className={`w-full text-left p-3 border-2 transition-all duration-200 ${
                    selectedMentality.id === m.id
                      ? 'bg-[#0D7377]/20 border-[#0D7377] shadow-pixel-green'
                      : 'bg-[#0A0A0F] border-[#2D2D44] hover:border-[#0D7377]/50'
                  }`}
                >
                  <p className={`font-bold ${selectedMentality.id === m.id ? m.color : 'text-white'}`}>
                    {m.name}
                  </p>
                  <p className="text-xs text-[#8B8BA7]">{m.desc}</p>
                </button>
              ))}
            </div>
          </Card>
        </div>

        {/* 中间 - 战术板 */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">战术板</h3>
              <div className="flex items-center gap-2 text-xs text-[#8B8BA7]">
                <span className="flex items-center gap-1"><span className="w-2 h-2 bg-amber-500"/>门将</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 bg-blue-500"/>后卫</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 bg-emerald-500"/>中场</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 bg-red-500"/>前锋</span>
              </div>
            </div>

            <div className="relative w-full aspect-[3/4] bg-[#065F46] border-4 border-[#2D2D44] overflow-hidden"
              style={{
                backgroundImage: `
                  linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
                  linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)
                `,
                backgroundSize: '20px 20px'
              }}
            >
              <div className="absolute inset-4 border-2 border-white/30" />
              <div className="absolute top-1/2 left-4 right-4 h-px bg-white/30" />
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-20 h-20 border-2 border-white/30 rounded-full" />

              {players.map((player) => {
                const group = player.position === 'GK' ? 'GK' : player.position === 'DF' ? 'DF' : player.position === 'MF' ? 'MF' : 'FW'
                posIndices[group] = (posIndices[group] || 0) + 1
                const coords = getPositionCoords(player.position, posIndices[group] - 1, posCounts[group] || 1)
                return (
                  <div
                    key={player.id}
                    className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group"
                    style={{ left: `${coords.x}%`, top: `${coords.y}%` }}
                  >
                    <div className={`w-10 h-10 border-2 border-white/80 flex items-center justify-center shadow-pixel transition-all group-hover:scale-110 ${
                      positionColors[group] || 'bg-[#2D2D44]'
                    }`}>
                      <span className="text-xs font-bold text-white">{player.position}</span>
                    </div>
                    <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 whitespace-nowrap">
                      <p className="text-[10px] text-white bg-black/60 px-1">{player.name}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>

          <Card>
            <h3 className="text-lg font-semibold mb-4">战术属性</h3>
            <div className="grid grid-cols-3 gap-6">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">进攻倾向</span>
                  <span className="text-sm font-bold stat-number text-red-400">{selectedFormation.attack}</span>
                </div>
                <div className="pixel-progress-track">
                  <div className="pixel-progress-fill bg-red-500" style={{ width: `${selectedFormation.attack}%` }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">防守稳固</span>
                  <span className="text-sm font-bold stat-number text-blue-400">{selectedFormation.defense}</span>
                </div>
                <div className="pixel-progress-track">
                  <div className="pixel-progress-fill bg-blue-500" style={{ width: `${selectedFormation.defense}%` }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">控球能力</span>
                  <span className="text-sm font-bold stat-number text-emerald-400">{selectedFormation.control}</span>
                </div>
                <div className="pixel-progress-track">
                  <div className="pixel-progress-fill bg-emerald-500" style={{ width: `${selectedFormation.control}%` }} />
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
