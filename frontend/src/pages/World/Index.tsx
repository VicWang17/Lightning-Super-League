import { useState } from 'react'
import { clsx } from 'clsx'
import { Link } from 'react-router-dom'
import {
  Globe,
  Trophy,
  Users,
  Target,
  ChevronRight,
  InfoBox,
} from '../../components/ui/pixel-icons'
import { Card } from '../../components/ui/Card'
import { useWorldRankings, useTopPlayers, useWorldRecords } from '../../hooks/useWorld'
import {
  type RecordItem,
  RecordCategory,
  RecordType,
  RECORD_CATEGORY_LABELS,
  RECORD_TYPE_LABELS,
  RECORD_TYPES_BY_CATEGORY,
} from '../../types/records'

type WorldTab = 'rankings' | 'players' | 'records'
type PlayerPosition = 'ALL' | 'FW' | 'MF' | 'DF' | 'GK'

const TABS = [
  { value: 'rankings' as WorldTab, label: '球队排名', icon: Trophy },
  { value: 'players' as WorldTab, label: '球员排名', icon: Users },
  { value: 'records' as WorldTab, label: '世界纪录', icon: Target },
]

const POSITION_FILTERS: { value: PlayerPosition; label: string }[] = [
  { value: 'ALL', label: '全部' },
  { value: 'FW', label: '前锋' },
  { value: 'MF', label: '中场' },
  { value: 'DF', label: '后卫' },
  { value: 'GK', label: '门将' },
]

const RANK_COLORS = [
  'bg-amber-500 text-black',
  'bg-slate-300 text-black',
  'bg-orange-400 text-black',
]

function RankingRow({ ranking }: { ranking: { rank: number; team_name: string; total_score: number; league_score: number; cup_score: number; cup_titles: number; team_id: string } }) {
  const rankColor = ranking.rank <= 3 ? RANK_COLORS[ranking.rank - 1] : 'bg-[#1E1E2D] text-[#8B8BA7]'

  return (
    <tr className="border-b border-[#2D2D44] hover:bg-[#1E1E2D]/50 transition-colors">
      <td className="py-3 px-4">
        <div className={`w-8 h-8 flex items-center justify-center text-sm font-bold pixel-number ${rankColor}`}>
          {ranking.rank}
        </div>
      </td>
      <td className="py-3 px-4">
        <Link
          to={`/teams/${ranking.team_id}`}
          className="font-medium text-white hover:text-[#C6F135] transition-colors"
        >
          {ranking.team_name}
        </Link>
      </td>
      <td className="py-3 px-4 text-center stat-number text-[#8B8BA7]">
        {ranking.league_score.toFixed(0)}
      </td>
      <td className="py-3 px-4 text-center stat-number text-amber-400">
        {ranking.cup_titles}
      </td>
      <td className="py-3 px-4 text-center">
        <span className="font-bold pixel-number text-lg text-[#C6F135]">
          {ranking.total_score.toFixed(0)}
        </span>
      </td>
    </tr>
  )
}

function PlayerRow({ player }: { player: { rank: number; player_name: string; avatar_url?: string; position: string; age: number; ovr: number; team_name: string; team_id: string; player_id: string } }) {
  const rankColor = player.rank <= 3 ? RANK_COLORS[player.rank - 1] : 'bg-[#1E1E2D] text-[#8B8BA7]'

  return (
    <tr className="border-b border-[#2D2D44] hover:bg-[#1E1E2D]/50 transition-colors">
      <td className="py-3 px-4">
        <div className={`w-8 h-8 flex items-center justify-center text-sm font-bold pixel-number ${rankColor}`}>
          {player.rank}
        </div>
      </td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-3">
          {player.avatar_url ? (
            <div className="w-10 h-10 bg-[#1E1E2D] border-2 border-[#2D2D44] overflow-hidden">
              <img src={`/${player.avatar_url}`} alt={player.player_name} className="w-full h-full object-cover" />
            </div>
          ) : (
            <div className="w-10 h-10 bg-[#0D4A4D]/30 border-2 border-[#0D7377]/30 flex items-center justify-center">
              <Users className="w-5 h-5 text-[#0D7377]" />
            </div>
          )}
          <Link
            to={`/players/${player.player_id}`}
            className="font-medium text-white hover:text-[#C6F135] transition-colors"
          >
            {player.player_name}
          </Link>
        </div>
      </td>
      <td className="py-3 px-4">
        <span className="px-2 py-0.5 text-xs bg-[#1E1E2D] border border-[#2D2D44] text-[#8B8BA7]">
          {player.position}
        </span>
      </td>
      <td className="py-3 px-4 text-center text-[#8B8BA7]">{player.age}</td>
      <td className="py-3 px-4 text-center">
        <span className="font-bold pixel-number text-lg text-[#C6F135]">{player.ovr}</span>
      </td>
      <td className="py-3 px-4">
        <Link
          to={`/teams/${player.team_id}`}
          className="text-sm text-[#8B8BA7] hover:text-white transition-colors"
        >
          {player.team_name}
        </Link>
      </td>
    </tr>
  )
}

function RecordCard({ record }: { record: RecordItem }) {
  const isPlayerRecord = record.category === RecordCategory.PLAYER

  return (
    <Card className="bg-[#12121A] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 transition-all">
      <div className="flex items-start gap-4">
        <div className="shrink-0">
          {isPlayerRecord && record.holder_avatar_url ? (
            <div className="w-12 h-12 bg-[#1E1E2D] border-2 border-[#2D2D44] overflow-hidden">
              <img src={`/${record.holder_avatar_url}`} alt={record.holder_name} className="w-full h-full object-cover" />
            </div>
          ) : (
            <div className="w-12 h-12 bg-[#0D4A4D]/30 border-2 border-[#0D7377]/30 flex items-center justify-center">
              <Trophy className="w-6 h-6 text-[#0D7377]" />
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-white truncate">{record.record_type_label}</h3>
            <span className="text-lg font-bold stat-number pixel-number text-[#C6F135]">{record.record_value}</span>
          </div>
          <div className="mt-1 flex items-center gap-2 text-sm">
            <span className="text-white font-medium">{record.holder_name}</span>
            {record.holder_team_name && <span className="text-[#8B8BA7]">· {record.holder_team_name}</span>}
          </div>
          <div className="mt-2 flex items-center gap-3 text-xs text-[#4B4B6A]">
            {record.season_number !== undefined && <span>第 {record.season_number} 赛季</span>}
            {record.match_date && <span>{record.match_date}</span>}
            {record.fixture_id && (
              <Link to={`/match/${record.fixture_id}`} className="inline-flex items-center gap-0.5 text-[#0D7377] hover:text-[#C6F135] transition-colors">
                查看比赛<ChevronRight className="w-3 h-3" />
              </Link>
            )}
          </div>
        </div>
      </div>
    </Card>
  )
}

function EmptyRecordCard({ recordType }: { recordType: RecordType }) {
  return (
    <Card className="bg-[#12121A] border-2 border-[#2D2D44]/60 opacity-60">
      <div className="flex items-start gap-4">
        <div className="shrink-0">
          <div className="w-12 h-12 bg-[#0D4A4D]/20 border-2 border-[#0D7377]/20 flex items-center justify-center">
            <Trophy className="w-6 h-6 text-[#0D7377]/50" />
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-[#8B8BA7] truncate">{RECORD_TYPE_LABELS[recordType]}</h3>
            <span className="text-lg font-bold stat-number pixel-number text-[#4B4B6A]">—</span>
          </div>
          <div className="mt-1 text-sm text-[#4B4B6A]">暂无该纪录</div>
        </div>
      </div>
    </Card>
  )
}

function WorldRecordsTab() {
  const [activeCategory, setActiveCategory] = useState<RecordCategory>(RecordCategory.PLAYER)
  const { records, loading } = useWorldRecords()

  const recordsByType = new Map<RecordType, RecordItem>()
  if (records) {
    records[activeCategory].forEach((r) => recordsByType.set(r.record_type, r))
  }
  const allRecordTypes = RECORD_TYPES_BY_CATEGORY[activeCategory]

  return (
    <div>
      <div className="flex gap-1 mb-6 border-b-2 border-[#2D2D44]">
        {[RecordCategory.PLAYER, RecordCategory.TEAM, RecordCategory.MATCH].map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={clsx(
              'px-4 py-2.5 text-sm font-medium border-b-2 -mb-0.5 transition-all',
              activeCategory === cat
                ? 'border-[#C6F135] text-[#C6F135]'
                : 'border-transparent text-[#8B8BA7] hover:text-white'
            )}
          >
            {RECORD_CATEGORY_LABELS[cat]}
            <span className="ml-1.5 text-xs opacity-60">
              ({records ? records[cat].length : 0}/{RECORD_TYPES_BY_CATEGORY[cat].length})
            </span>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-16 text-[#8B8BA7]">加载中...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {allRecordTypes.map((type) => {
            const record = recordsByType.get(type)
            return record ? <RecordCard key={type} record={record} /> : <EmptyRecordCard key={type} recordType={type} />
          })}
        </div>
      )}
    </div>
  )
}

function WorldPage() {
  const [activeTab, setActiveTab] = useState<WorldTab>('rankings')
  const [playerPosition, setPlayerPosition] = useState<PlayerPosition>('ALL')

  const { rankings, loading: rankingsLoading } = useWorldRankings()
  const { players, loading: playersLoading } = useTopPlayers(100, playerPosition === 'ALL' ? undefined : playerPosition)

  return (
    <div className="max-w-[1200px]">
      {/* 页面标题 */}
      <div className="flex items-center gap-3 mb-6">
        <Globe className="w-7 h-7 text-[#C6F135]" />
        <h1 className="text-2xl font-bold pixel-title">世界</h1>
      </div>

      {/* Tab 导航 */}
      <div className="flex flex-wrap gap-2 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-2 transition-all flex items-center gap-2',
              activeTab === tab.value
                ? 'bg-[#C6F135] text-[#0A0A0F] border-[#C6F135]'
                : 'bg-[#12121A] text-[#8B8BA7] border-[#2D2D44] hover:border-[#0D7377] hover:text-white'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 内容 */}
      <div className="card">
        {activeTab === 'rankings' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">球队世界排名</h3>
              <span className="text-xs text-[#4B4B6A]">近3个赛季联赛加权积分 + 杯赛冠军积分</span>
            </div>
            {rankingsLoading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="h-12 bg-[#1E1E2D] animate-pulse" />
                ))}
              </div>
            ) : rankings.length === 0 ? (
              <div className="text-center py-12">
                <Trophy className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
                <p className="text-[#8B8BA7]">暂无排名数据</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-xs text-[#8B8BA7] border-b border-[#2D2D44]">
                      <th className="py-2 px-4 font-medium">排名</th>
                      <th className="py-2 px-4 font-medium">球队</th>
                      <th className="py-2 px-4 font-medium text-center">
                        <span className="inline-flex items-center gap-1">
                          联赛积分
                          <span title="联赛积分 = 近3赛季联赛积分 × 联赛权重（超级×10 / 甲级×5 / 乙级×2.5 / 丙级×1）">
                            <InfoBox className="w-3.5 h-3.5 text-[#4B4B6A] hover:text-[#0D7377] cursor-help" />
                          </span>
                        </span>
                      </th>
                      <th className="py-2 px-4 font-medium text-center">杯赛冠军</th>
                      <th className="py-2 px-4 font-medium text-center">总得分</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rankings.map((ranking) => (
                      <RankingRow key={ranking.team_id} ranking={ranking} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'players' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">球员OVR排名</h3>
              <div className="flex gap-1">
                {POSITION_FILTERS.map((filter) => (
                  <button
                    key={filter.value}
                    onClick={() => setPlayerPosition(filter.value)}
                    className={clsx(
                      'px-3 py-1 text-xs font-medium border-2 transition-all',
                      playerPosition === filter.value
                        ? 'bg-[#C6F135] text-[#0A0A0F] border-[#C6F135]'
                        : 'bg-[#12121A] text-[#8B8BA7] border-[#2D2D44] hover:border-[#0D7377]'
                    )}
                  >
                    {filter.label}
                  </button>
                ))}
              </div>
            </div>
            {playersLoading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="h-14 bg-[#1E1E2D] animate-pulse" />
                ))}
              </div>
            ) : players.length === 0 ? (
              <div className="text-center py-12">
                <Users className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
                <p className="text-[#8B8BA7]">暂无球员数据</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-xs text-[#8B8BA7] border-b border-[#2D2D44]">
                      <th className="py-2 px-4 font-medium">排名</th>
                      <th className="py-2 px-4 font-medium">球员</th>
                      <th className="py-2 px-4 font-medium">位置</th>
                      <th className="py-2 px-4 font-medium text-center">年龄</th>
                      <th className="py-2 px-4 font-medium text-center">OVR</th>
                      <th className="py-2 px-4 font-medium">球队</th>
                    </tr>
                  </thead>
                  <tbody>
                    {players.map((player) => (
                      <PlayerRow key={player.player_id} player={player} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'records' && <WorldRecordsTab />}
      </div>
    </div>
  )
}

export default WorldPage
