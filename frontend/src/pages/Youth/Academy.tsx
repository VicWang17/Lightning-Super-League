import { useNavigate } from 'react-router-dom'
import { Loader } from '../../components/ui/pixel-icons'
import { PageHeader } from '../../components/ui/PageHeader'
import { YouthTabs } from '../../components/youth/YouthTabs'
import { Card, CardContent } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Avatar from '../../components/ui/Avatar'
import { useYouthAcademy } from '../../hooks/useYouthAcademy'

const growthSpeedLabels: Record<string, string> = {
  fast: '快',
  normal: '中',
  slow: '慢',
}

const growthSpeedVariants: Record<string, 'success' | 'warning' | 'default'> = {
  fast: 'success',
  normal: 'warning',
  slow: 'default',
}

const positionColors: Record<string, string> = {
  FW: 'bg-[#FF6F59] text-[#F8FFD2]',
  MF: 'bg-[#1F5F43] text-[#173126]',
  DF: 'bg-[#59C7EE] text-[#173126]',
  GK: 'bg-[#FFC247] text-[#173126]',
}

export default function YouthAcademy() {
  const navigate = useNavigate()
  const { data, rosterFull, loading, error } = useYouthAcademy()
  const players = data?.players ?? []

  if (loading) {
    return (
      <div className="max-w-[1400px] p-8 text-center text-[#466353]">
        <Loader className="w-6 h-6 animate-spin mx-auto mb-2" />
        加载青训数据中...
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-[1400px] p-8">
        <div className="p-4 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30 text-[#FF6F59] text-sm">
          {error}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <button
        onClick={() => navigate(-1)}
        className="text-sm text-[#466353] hover:text-[#173126] transition-colors"
      >
        返回上一页
      </button>

      <PageHeader
        title="青训营"
        subtitle="17-18 岁 Rookie · 赛季末未签约将流入新人市场"
      />

      <YouthTabs />

      {rosterFull && (
        <div className="p-3 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30">
          <p className="text-sm text-[#FF6F59]">
            一线队已满 18 人，无法签约新球员。请先清理阵容或等待球员离队。
          </p>
        </div>
      )}

      <Card>
        <CardContent className="p-4">
          {players.length === 0 ? (
            <div className="text-center py-12 text-[#466353]">
              <p className="text-sm mb-2">暂无在营球员</p>
              <p className="text-xs text-[#8B5A2B]/40">
                青训营将在赛季第 4 天和第 8 天自动刷新，最多补满 {data?.capacity ?? 8} 人
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {players.map((p) => (
                <button
                  key={p.academy_player_id}
                  onClick={() => navigate(`/youth/academy/${p.academy_player_id}`)}
                  className="text-left bg-white/70 border-2 border-[#1F5F43]/20 hover:border-[#1F5F43] p-4 transition-all"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <Avatar
                        src={p.avatar_url ? `/${p.avatar_url}` : undefined}
                        name={p.name}
                        size="md"
                      />
                      <div>
                        <h4 className="font-bold text-[#173126]">{p.name}</h4>
                        <p className="text-xs text-[#466353]">{p.age}岁 · 入营第{p.joined_day}天</p>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1.5">
                      <span className={`text-xs px-2 py-0.5 font-bold ${positionColors[p.position] || 'bg-[#F8FFD2] text-[#173126]'}`}>
                        {p.position}
                      </span>
                      <Badge variant={growthSpeedVariants[p.growth_speed] || 'default'} size="sm">
                        {growthSpeedLabels[p.growth_speed] || p.growth_speed}速成长
                      </Badge>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2">
                    <div className="p-2 bg-[#FFF8DC]/80 text-center">
                      <p className="text-xs text-[#466353]">OVR</p>
                      <p className="text-lg font-bold text-[#173126] stat-number">{p.ovr}</p>
                    </div>
                    <div className="p-2 bg-[#FFF8DC]/80 text-center">
                      <p className="text-xs text-[#466353]">潜力</p>
                      <p className={`text-lg font-bold ${
                        p.potential_letter === 'S' ? 'text-[#C77A00]' :
                        p.potential_letter === 'A' ? 'text-[#1F5F43]' :
                        'text-[#173126]'
                      } stat-number`}>
                        {p.potential_letter}
                      </p>
                    </div>
                    <div className="p-2 bg-[#FFF8DC]/80 text-center">
                      <p className="text-xs text-[#466353]">最近训练</p>
                      <p className="text-sm font-medium text-[#173126]">
                        {p.last_trained_day ? `第${p.last_trained_day}天` : '未训练'}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
