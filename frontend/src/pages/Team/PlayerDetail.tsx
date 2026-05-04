import { useParams, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Weight, Footprints } from 'lucide-react'
import {
  Clock, ChevronLeft, Calendar,
  TrendingUp, Award, Ruler, User, Shield, Target, Zap
} from '../../components/ui/pixel-icons'
import { Card } from '../../components/ui/Card'
import { getPositionColor, type Player } from '../../types/player'
import { api } from '../../api/client'

function PlayerDetail() {
  const { id } = useParams<{ id: string }>()
  const [player, setPlayer] = useState<Player | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    api.get<Player>(`/players/${id}`)
      .then(res => {
        if (res.success) {
          setPlayer(res.data)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return <div className="max-w-[1200px] p-8 text-center text-[#8B8BA7]">加载中...</div>
  }

  if (!player) {
    return <div className="max-w-[1200px] p-8 text-center text-red-400">球员未找到</div>
  }

  const statusNames: Record<string, string> = {
    ACTIVE: '健康',
    INJURED: '受伤',
    SUSPENDED: '停赛',
    RETIRED: '退役',
  }

  const statusColors: Record<string, string> = {
    ACTIVE: 'text-emerald-400',
    INJURED: 'text-red-400',
    SUSPENDED: 'text-amber-400',
    RETIRED: 'text-[#8B8BA7]',
  }

  const formNames: Record<string, string> = {
    HOT: '火热',
    GOOD: '良好',
    NEUTRAL: '平淡',
    LOW: '低迷',
  }

  const formColors: Record<string, string> = {
    HOT: 'text-red-400',
    GOOD: 'text-emerald-400',
    NEUTRAL: 'text-[#8B8BA7]',
    LOW: 'text-amber-400',
  }

  const squadRoleNames: Record<string, string> = {
    key_player: '核心球员',
    first_team: '一线队',
    rotation: '轮换',
    backup: '替补',
    hot_prospect: '希望之星',
    youngster: '青训',
    not_needed: '不需要',
  }

  const footMap: Record<string, string> = {
    RIGHT: '右脚',
    LEFT: '左脚',
    BOTH: '双脚',
  }

  // 核心属性按位置分组展示
  const abilityGroups = [
    {
      title: '进攻',
      icon: <Target className="w-4 h-4 text-red-400" />,
      color: 'bg-red-500',
      attrs: [
        { label: '射门', key: 'sho' },
        { label: '远射', key: 'fin' },
      ],
    },
    {
      title: '技术',
      icon: <Zap className="w-4 h-4 text-[#0D7377]" />,
      color: 'bg-[#0D7377]',
      attrs: [
        { label: '传球', key: 'pas' },
        { label: '视野', key: 'vis' },
        { label: '盘带', key: 'dri' },
        { label: '控球', key: 'con' },
        { label: '传中', key: 'cro' },
        { label: '球商', key: 'dec' },
      ],
    },
    {
      title: '身体',
      icon: <User className="w-4 h-4 text-emerald-400" />,
      color: 'bg-emerald-500',
      attrs: [
        { label: '速度', key: 'spd' },
        { label: '爆发力', key: 'acc' },
        { label: '力量', key: 'str' },
        { label: '体能', key: 'sta' },
        { label: '头球', key: 'hea' },
        { label: '平衡', key: 'bal' },
      ],
    },
    {
      title: '防守',
      icon: <Shield className="w-4 h-4 text-blue-400" />,
      color: 'bg-blue-500',
      attrs: [
        { label: '站位', key: 'defe' },
        { label: '抢断', key: 'tkl' },
      ],
    },
    {
      title: '定位球',
      icon: <Target className="w-4 h-4 text-amber-400" />,
      color: 'bg-amber-500',
      attrs: [
        { label: '定位球', key: 'set' },
      ],
    },
  ]

  const gkAbilityGroups = [
    {
      title: '门将专属',
      icon: <Shield className="w-4 h-4 text-amber-400" />,
      color: 'bg-amber-500',
      attrs: [
        { label: '扑救', key: 'sav' },
        { label: '反应', key: 'ref' },
        { label: '跑位', key: 'pos' },
        { label: '镇定', key: 'com' },
        { label: '球商', key: 'dec' },
        { label: '定位球', key: 'set' },
      ],
    },
  ]

  const groups = player.position === 'GK' ? gkAbilityGroups : abilityGroups

  return (
    <div className="max-w-[1200px]">
      {/* 返回按钮 */}
      <Link
        to={`/teams/${player.team_id}`}
        className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors mb-4"
      >
        <ChevronLeft className="w-4 h-4" />
        返回球队
      </Link>

      {/* 球员信息头部 */}
      <Card className="mb-6 bg-[#0D4A4D]/30 border-2 border-[#2D2D44] hover:-translate-y-1 hover:shadow-pixel transition-all">
        <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
          {/* 头像 */}
          <div className="w-28 h-28 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center shadow-pixel overflow-hidden">
            {player.avatar_url ? (
              <img src={`/${player.avatar_url}`} alt={player.name} className="w-full h-full object-cover" />
            ) : (
              <span className="text-5xl">👤</span>
            )}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-white">{player.name}</h1>
              <span className={`px-2 py-0.5 rounded-none text-xs font-medium ${getPositionColor(player.position)}`}>
                {player.position}
              </span>
              <span className="px-2 py-0.5 rounded-none text-xs font-bold bg-[#1E1E2D] border border-[#0D7377] text-[#0D7377]">
                潜力 {player.potential_letter}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm text-[#8B8BA7]">
              <div className="flex items-center gap-1.5">
                <Calendar className="w-4 h-4" />
                {player.age} 岁
              </div>
              <div className="flex items-center gap-1.5">
                <Ruler className="w-4 h-4" />
                {player.height} cm
              </div>
              <div className="flex items-center gap-1.5">
                <Weight className="w-4 h-4" />
                {player.weight} kg
              </div>
              <div className="flex items-center gap-1.5">
                <Footprints className="w-4 h-4" />
                {footMap[player.preferred_foot]}
              </div>
            </div>
            <div className="mt-3 flex items-center gap-4">
              <span className={`text-sm ${statusColors[player.status]}`}>
                ● {statusNames[player.status]}
              </span>
              <span className={`text-sm ${formColors[player.match_form]}`}>
                {formNames[player.match_form]}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="text-4xl font-bold stat-number pixel-number text-[#0D7377]">{player.ovr}</div>
              <div className="text-xs text-[#8B8BA7]">当前能力</div>
            </div>
          </div>
        </div>
      </Card>

      {/* 招牌技能 */}
      {player.skills && player.skills.length > 0 && (
        <Card className="mb-6" hover>
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Award className="w-5 h-5 text-amber-400" />
            招牌技能
          </h3>
          <div className="flex flex-wrap gap-2">
            {player.skills.map((skill, idx) => (
              <span
                key={idx}
                className={`px-3 py-1 text-sm border ${
                  skill.rarity === '传奇'
                    ? 'border-amber-500 text-amber-400 bg-amber-500/10'
                    : skill.rarity === '稀有'
                    ? 'border-[#0D7377] text-[#0D7377] bg-[#0D7377]/10'
                    : skill.rarity === '负面'
                    ? 'border-red-500 text-red-400 bg-red-500/10'
                    : 'border-[#8B8BA7] text-[#8B8BA7] bg-[#8B8BA7]/10'
                }`}
              >
                {skill.skill_id}
                <span className="text-xs opacity-70 ml-1">({skill.rarity})</span>
              </span>
            ))}
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧 - 详细能力 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 能力值 */}
          <Card hover>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-[#0D7377]" />
              详细能力
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {groups.map(group => (
                <div key={group.title} className="space-y-3">
                  <h4 className="text-sm font-medium text-[#8B8BA7] flex items-center gap-2">
                    {group.icon}
                    {group.title}
                  </h4>
                  {group.attrs.map(({ label, key }) => {
                    const val = (player.abilities as any)?.[key] ?? (player as any)[key] ?? 0
                    return (
                      <div key={key}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm">{label}</span>
                          <span className="font-bold stat-number pixel-number">{val}</span>
                        </div>
                        <div className="pixel-progress-track">
                          <div
                            className={`pixel-progress-fill ${group.color}`}
                            style={{ width: `${(val / 20) * 100}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          </Card>

          {/* 合同信息 */}
          <Card hover>
            <h3 className="text-lg font-semibold mb-4">合同信息</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 bg-[#1E1E2D]">
                <p className="text-xs text-[#8B8BA7] mb-1">工资</p>
                <p className="font-bold stat-number pixel-number text-white">€{(player.wage / 1000).toFixed(0)}K</p>
              </div>
              <div className="p-4 bg-[#1E1E2D]">
                <p className="text-xs text-[#8B8BA7] mb-1">合同到期</p>
                <p className="font-bold stat-number pixel-number text-white">第 {player.contract_end_season} 赛季</p>
              </div>
              <div className="p-4 bg-[#1E1E2D]">
                <p className="text-xs text-[#8B8BA7] mb-1">解约金</p>
                <p className="font-bold stat-number pixel-number text-emerald-400">€{(player.release_clause! / 1000000).toFixed(1)}M</p>
              </div>
              <div className="p-4 bg-[#1E1E2D]">
                <p className="text-xs text-[#8B8BA7] mb-1">市场价值</p>
                <p className="font-bold stat-number pixel-number text-[#0D7377]">€{(player.market_value / 1000000).toFixed(1)}M</p>
              </div>
            </div>
          </Card>
        </div>

        {/* 右侧 - 统计和状态 */}
        <div className="space-y-6">
          {/* 本赛季统计 */}
          <Card hover>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-[#0D7377]" />
              本赛季统计
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 bg-[#1E1E2D]">
                <div className="text-2xl font-bold stat-number pixel-number text-white">{player.matches_played}</div>
                <div className="text-xs text-[#8B8BA7]">出场</div>
              </div>
              <div className="text-center p-4 bg-[#1E1E2D]">
                <div className="text-2xl font-bold stat-number pixel-number text-emerald-400">{player.goals}</div>
                <div className="text-xs text-[#8B8BA7]">进球</div>
              </div>
              <div className="text-center p-4 bg-[#1E1E2D]">
                <div className="text-2xl font-bold stat-number pixel-number text-[#0D7377]">{player.assists}</div>
                <div className="text-xs text-[#8B8BA7]">助攻</div>
              </div>
              <div className="text-center p-4 bg-[#1E1E2D]">
                <div className="text-2xl font-bold stat-number pixel-number text-amber-400">{player.average_rating}</div>
                <div className="text-xs text-[#8B8BA7]">场均评分</div>
              </div>
            </div>
            <div className="mt-4 pt-4 border-t-2 border-[#2D2D44] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#8B8BA7]">黄牌</span>
                <span className="font-bold stat-number pixel-number text-yellow-400">{player.yellow_cards}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#8B8BA7]">红牌</span>
                <span className="font-bold stat-number pixel-number text-red-400">{player.red_cards}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#8B8BA7]">出场时间</span>
                <span className="font-bold stat-number pixel-number">{player.minutes_played} 分钟</span>
              </div>
            </div>
          </Card>

          {/* 状态 */}
          <Card hover>
            <h3 className="text-lg font-semibold mb-4">当前状态</h3>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">体能</span>
                  <span className="font-bold stat-number pixel-number">{player.fitness}%</span>
                </div>
                <div className="pixel-progress-track">
                  <div
                    className={`pixel-progress-fill ${player.fitness > 80 ? 'bg-emerald-500' : player.fitness > 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                    style={{ width: `${player.fitness}%` }}
                  />
                </div>
              </div>
            </div>
          </Card>

          {/* 角色 */}
          <Card hover>
            <h3 className="text-lg font-semibold mb-4">球队角色</h3>
            <div className="p-4 bg-[#0D4A4D]/30 border-2 border-[#0D7377]/30">
              <p className="font-medium text-white">{squadRoleNames[player.squad_role]}</p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default PlayerDetail
