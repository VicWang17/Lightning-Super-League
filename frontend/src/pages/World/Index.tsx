import { useState, useEffect } from 'react'
import { clsx } from 'clsx'
import { Link, useNavigate } from 'react-router-dom'
import {
  Users,
  ChevronRight,
  InfoBox,
} from '../../components/ui/pixel-icons'
import { useWorldRankings, useTopPlayers, useWorldRecords, useWorldLeaderboard, useWorldTeamLeaderboard } from '../../hooks/useWorld'
import { useSeasonAwards, useAllLeagueAwardsForSeason } from '../../hooks/useAwards'
import { useSeason } from '../../hooks/useSeason'
import { useSeasons } from '../../hooks/useSeasons'
import { AwardCard, DataKingsRow, TeamOfSeasonGrid } from '../../components/awards'

import type { LeaderboardType, LeaderboardItem, TeamLeaderboardType, TeamLeaderboardItem } from '../../types/leaderboard'
import type { TopPlayer } from '../../types/world'
import { LeaderboardValue } from '../../components/leaderboard/LeaderboardValue'
import { RecordsBoard } from '../../components/records/RecordsBoard'
import { PageHeader } from '../../components/ui/PageHeader'
import { SegmentedTabs } from '../../components/ui/SegmentedTabs'

type WorldTab = 'rankings' | 'players' | 'records' | 'awards'
type PlayerPosition = 'ALL' | 'FW' | 'MF' | 'DF' | 'GK'
type WorldSortType = 'ovr' | LeaderboardType

interface WorldSortOption {
  value: WorldSortType
  label: string
  format: 'int' | 'float1' | 'percent'
}

const WORLD_SORT_OPTIONS: WorldSortOption[] = [
  { value: 'ovr', label: 'OVR', format: 'int' },
  { value: 'goals', label: '进球', format: 'int' },
  { value: 'assists', label: '助攻', format: 'int' },
  { value: 'average_rating', label: '场均评分', format: 'float1' },
  { value: 'tackles', label: '抢断', format: 'int' },
  { value: 'interceptions', label: '拦截', format: 'int' },
  { value: 'clearances', label: '解围', format: 'int' },
  { value: 'blocks', label: '封堵', format: 'int' },
  { value: 'saves', label: '扑救', format: 'int' },
  { value: 'clean_sheets', label: '零封', format: 'int' },
  { value: 'shots', label: '射门', format: 'int' },
  { value: 'shots_on_target', label: '射正', format: 'int' },
  { value: 'shot_accuracy', label: '射正率', format: 'percent' },
  { value: 'key_passes', label: '关键传球', format: 'int' },
  { value: 'passes', label: '传球', format: 'int' },
  { value: 'pass_accuracy', label: '传球成功率', format: 'percent' },
  { value: 'dribbles', label: '盘带', format: 'int' },
  { value: 'yellow_cards', label: '黄牌', format: 'int' },
  { value: 'red_cards', label: '红牌', format: 'int' },
  { value: 'fouls', label: '犯规', format: 'int' },
  { value: 'offsides', label: '越位', format: 'int' },
  { value: 'touches', label: '触球', format: 'int' },
  { value: 'minutes_played', label: '出场时间', format: 'int' },
  { value: 'matches_played', label: '出场', format: 'int' },
  { value: 'goals_per_game', label: '场均进球', format: 'float1' },
  { value: 'assists_per_game', label: '场均助攻', format: 'float1' },
]

type WorldTeamSortType = 'ranking' | TeamLeaderboardType

interface WorldTeamSortOption {
  value: WorldTeamSortType
  label: string
  format: 'int' | 'float1' | 'percent'
}

const TEAM_SORT_OPTIONS: WorldTeamSortOption[] = [
  { value: 'ranking', label: '综合排名', format: 'int' },
  { value: 'points', label: '积分', format: 'int' },
  { value: 'wins', label: '胜场', format: 'int' },
  { value: 'draws', label: '平局', format: 'int' },
  { value: 'losses', label: '负场', format: 'int' },
  { value: 'matches', label: '比赛', format: 'int' },
  { value: 'goals_for', label: '进球', format: 'int' },
  { value: 'goals_against', label: '失球', format: 'int' },
  { value: 'goal_difference', label: '净胜球', format: 'int' },
  { value: 'win_rate', label: '胜率', format: 'percent' },
  { value: 'goals_per_game', label: '场均进球', format: 'float1' },
  { value: 'goals_against_per_game', label: '场均失球', format: 'float1' },
]

const TABS = [
  { value: 'rankings' as WorldTab, label: '球队排名' },
  { value: 'players' as WorldTab, label: '球员排名' },
  { value: 'records' as WorldTab, label: '世界纪录' },
  { value: 'awards' as WorldTab, label: '赛季奖项' },
]

const POSITION_FILTERS: { value: PlayerPosition; label: string }[] = [
  { value: 'ALL', label: '全部' },
  { value: 'FW', label: '前锋' },
  { value: 'MF', label: '中场' },
  { value: 'DF', label: '后卫' },
  { value: 'GK', label: '门将' },
]

const RANK_COLORS = [
  'bg-[#FFC247] text-[#173126]',
  'bg-[#B9D3A8] text-[#173126]',
  'bg-[#FF6F59] text-[#173126]',
]

function RankingRow({ ranking }: { ranking: { rank: number; team_name: string; total_score: number; league_score: number; cup_score: number; cup_titles: number; team_id: string } }) {
  const rankColor = ranking.rank <= 3 ? RANK_COLORS[ranking.rank - 1] : 'bg-[#FFF8DC]/80 text-[#466353]'

  return (
    <tr className="border-b border-[#1F5F43]/20 hover:bg-[#FFF8DC]/80 transition-colors">
      <td className="py-3 px-4">
        <div className={`w-8 h-8 flex items-center justify-center text-sm font-bold pixel-number ${rankColor}`}>
          {ranking.rank}
        </div>
      </td>
      <td className="py-3 px-4">
        <Link
          to={`/teams/${ranking.team_id}`}
          className="font-medium text-[#173126] hover:text-[#1F5F43] transition-colors"
        >
          {ranking.team_name}
        </Link>
      </td>
      <td className="py-3 px-4 text-center stat-number text-[#466353]">
        {ranking.league_score.toFixed(0)}
      </td>
      <td className="py-3 px-4 text-center stat-number text-[#C77A00]">
        {ranking.cup_titles}
      </td>
      <td className="py-3 px-4 text-center">
        <span className="font-bold pixel-number text-lg text-[#1F5F43]">
          {ranking.total_score.toFixed(0)}
        </span>
      </td>
    </tr>
  )
}

function TeamLeaderboardRow({ item, format }: { item: TeamLeaderboardItem; format: 'int' | 'float1' | 'percent' }) {
  const rankColor = item.rank <= 3 ? RANK_COLORS[item.rank - 1] : 'bg-[#FFF8DC]/80 text-[#466353]'

  return (
    <tr className="border-b border-[#1F5F43]/20 hover:bg-[#FFF8DC]/80 transition-colors">
      <td className="py-3 px-4">
        <div className={`w-8 h-8 flex items-center justify-center text-sm font-bold pixel-number ${rankColor}`}>
          {item.rank}
        </div>
      </td>
      <td className="py-3 px-4">
        <Link
          to={`/teams/${item.team_id}`}
          className="font-medium text-[#173126] hover:text-[#1F5F43] transition-colors"
        >
          {item.team_name}
        </Link>
      </td>
      <td className="py-3 px-4 text-center text-[#466353]">{item.matches > 0 ? `${item.matches}场` : '-'}</td>
      <td className="py-3 px-4 text-center">
        <span className="font-bold pixel-number text-lg text-[#1F5F43]">
          <LeaderboardValue value={item.value} format={format} />
        </span>
      </td>
    </tr>
  )
}

function PlayerRow({ player }: { player: { rank: number; player_name: string; avatar_url?: string; position: string; age: number; ovr: number; team_name: string; team_id: string; player_id: string } }) {
  const rankColor = player.rank <= 3 ? RANK_COLORS[player.rank - 1] : 'bg-[#FFF8DC]/80 text-[#466353]'

  return (
    <tr className="border-b border-[#1F5F43]/20 hover:bg-[#FFF8DC]/80 transition-colors">
      <td className="py-3 px-4">
        <div className={`w-8 h-8 flex items-center justify-center text-sm font-bold pixel-number ${rankColor}`}>
          {player.rank}
        </div>
      </td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-3">
          {player.avatar_url ? (
            <div className="w-10 h-10 bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 overflow-hidden">
              <img src={`/${player.avatar_url}`} alt={player.player_name} className="w-full h-full object-cover" />
            </div>
          ) : (
            <div className="w-10 h-10 bg-[#B9EF3F]/20 border-2 border-[#1F5F43]/25 flex items-center justify-center">
              <Users className="w-5 h-5 text-[#1F5F43]" />
            </div>
          )}
          <Link
            to={`/players/${player.player_id}`}
            className="font-medium text-[#173126] hover:text-[#1F5F43] transition-colors"
          >
            {player.player_name}
          </Link>
        </div>
      </td>
      <td className="py-3 px-4">
        <span className="px-2 py-0.5 text-xs bg-[#FFF8DC]/80 border border-[#1F5F43]/20 text-[#466353]">
          {player.position}
        </span>
      </td>
      <td className="py-3 px-4 text-center text-[#466353]">{player.age}</td>
      <td className="py-3 px-4 text-center">
        <span className="font-bold pixel-number text-lg text-[#1F5F43]">{player.ovr}</span>
      </td>
      <td className="py-3 px-4">
        <Link
          to={`/teams/${player.team_id}`}
          className="text-sm text-[#466353] hover:text-[#173126] transition-colors"
        >
          {player.team_name}
        </Link>
      </td>
    </tr>
  )
}

function LeaderboardPlayerRow({ item, format }: { item: { rank: number; player_name: string; avatar_url?: string; position: string; team_name: string; team_id: string; player_id: string; value: number; matches: number }; format: 'int' | 'float1' | 'percent' }) {
  const rankColor = item.rank <= 3 ? RANK_COLORS[item.rank - 1] : 'bg-[#FFF8DC]/80 text-[#466353]'

  return (
    <tr className="border-b border-[#1F5F43]/20 hover:bg-[#FFF8DC]/80 transition-colors">
      <td className="py-3 px-4">
        <div className={`w-8 h-8 flex items-center justify-center text-sm font-bold pixel-number ${rankColor}`}>
          {item.rank}
        </div>
      </td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-3">
          {item.avatar_url ? (
            <div className="w-10 h-10 bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 overflow-hidden">
              <img src={`/${item.avatar_url}`} alt={item.player_name} className="w-full h-full object-cover" />
            </div>
          ) : (
            <div className="w-10 h-10 bg-[#B9EF3F]/20 border-2 border-[#1F5F43]/25 flex items-center justify-center">
              <Users className="w-5 h-5 text-[#1F5F43]" />
            </div>
          )}
          <Link
            to={`/players/${item.player_id}`}
            className="font-medium text-[#173126] hover:text-[#1F5F43] transition-colors"
          >
            {item.player_name}
          </Link>
        </div>
      </td>
      <td className="py-3 px-4">
        <span className="px-2 py-0.5 text-xs bg-[#FFF8DC]/80 border border-[#1F5F43]/20 text-[#466353]">
          {item.position}
        </span>
      </td>
      <td className="py-3 px-4 text-center text-[#466353]">{item.matches > 0 ? `${item.matches}场` : '-'}</td>
      <td className="py-3 px-4 text-center">
        <span className="font-bold pixel-number text-lg text-[#1F5F43]">
          <LeaderboardValue value={item.value} format={format} />
        </span>
      </td>
      <td className="py-3 px-4">
        <Link
          to={`/teams/${item.team_id}`}
          className="text-sm text-[#466353] hover:text-[#173126] transition-colors"
        >
          {item.team_name}
        </Link>
      </td>
    </tr>
  )
}

function WorldRecordsTab() {
  const { records, loading } = useWorldRecords()
  return <RecordsBoard records={records} loading={loading} emptyText="暂无世界纪录" />
}

function WorldAwardsTab() {
  const { seasons, loading: seasonsLoading } = useSeasons()
  const { season: currentSeason } = useSeason()
  const [selectedSeasonId, setSelectedSeasonId] = useState<string | undefined>(currentSeason?.id)

  // 默认选中当前赛季
  useEffect(() => {
    if (currentSeason?.id && !selectedSeasonId) {
      setSelectedSeasonId(currentSeason.id)
    }
  }, [currentSeason?.id, selectedSeasonId])

  const selectedSeason = seasons.find(s => s.id === selectedSeasonId)

  const { awards, loading: seasonAwardsLoading } = useSeasonAwards(selectedSeasonId)
  const { leagueAwards, loading: leagueAwardsLoading } = useAllLeagueAwardsForSeason(selectedSeasonId)

  const loading = seasonAwardsLoading || leagueAwardsLoading || seasonsLoading

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-10 bg-[#FFF8DC]/80 animate-pulse max-w-[200px]" />
        <div className="h-48 bg-[#FFF8DC]/80 animate-pulse" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-32 bg-[#FFF8DC]/80 animate-pulse" />)}
        </div>
      </div>
    )
  }

  // 过滤出有数据的联赛奖项
  const activeLeagueAwards = leagueAwards.filter(la => la.team_of_season.length > 0 || la.golden_boot || la.best_fw)

  return (
    <div className="space-y-8">
      {/* 赛季选择器 */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-[#466353]">赛季</span>
        <div className="relative">
          <select
            value={selectedSeasonId || ''}
            onChange={(e) => setSelectedSeasonId(e.target.value)}
            className="appearance-none bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 text-[#173126] text-sm px-4 py-2 pr-8 focus:outline-none focus:border-[#1F5F43] cursor-pointer"
          >
            {seasons.map((season) => (
              <option key={season.id} value={season.id}>
                第 {season.season_number} 赛季
              </option>
            ))}
          </select>
          <ChevronRight className="w-4 h-4 text-[#466353] absolute right-2 top-1/2 -translate-y-1/2 rotate-90 pointer-events-none" />
        </div>
        {selectedSeason && (
          <span className="text-xs text-[#8B5A2B]/40">
            {selectedSeason.status === 'finished' ? '已结束' : '进行中'}
          </span>
        )}
      </div>

      {/* 闪电足球先生 */}
      <section >
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1 h-5 bg-[#B9EF3F]" />
          <h3 className="text-lg font-bold text-[#173126]">闪电足球先生</h3>
        </div>
        {awards?.best_player ? (
          <div className="max-w-sm mx-auto">
            <div className="relative bg-[#1F5F43] border-2 border-[#B9EF3F]/30 p-6 overflow-hidden">
              <div className="absolute inset-0 opacity-[0.05] bg-[radial-gradient(circle_at_50%_0%,_#B9EF3F,_transparent_70%)]" />
              <div className="absolute top-0 left-0 right-0 h-px bg-[linear-gradient(90deg,transparent,#B9EF3F,transparent)]" />
              <div className="relative flex flex-col items-center text-center">
                <span className="text-6xl mb-4 drop-shadow-lg">👑</span>
                <h4 className="text-xl font-bold text-[#173126] mb-2">
                  {awards.best_player.player_name}
                </h4>
                <Link
                  to={`/players/${awards.best_player.player_id}`}
                  className="text-sm text-[#1F5F43] hover:underline mb-3"
                >
                  查看球员详情
                </Link>
                {awards.best_player.metadata && (
                  <div className="flex flex-wrap justify-center gap-3 text-xs text-[#466353]">
                    {awards.best_player.metadata.rating !== undefined && (
                      <span className="px-2 py-1 bg-[#FFF8DC]/80 border border-[#1F5F43]/20">
                        评分 {awards.best_player.metadata.rating.toFixed(1)}
                      </span>
                    )}
                    {awards.best_player.metadata.championships !== undefined && (
                      <span className="px-2 py-1 bg-[#FFF8DC]/80 border border-[#1F5F43]/20">
                        {awards.best_player.metadata.championships} 座冠军
                      </span>
                    )}
                    {awards.best_player.metadata.mvp_count !== undefined && (
                      <span className="px-2 py-1 bg-[#FFF8DC]/80 border border-[#1F5F43]/20">
                        {awards.best_player.metadata.mvp_count} 次 MVP
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-12 border border-[#1F5F43]/20 bg-white/70">
            <span className="text-3xl opacity-30 grayscale">👑</span>
            <p className="text-sm text-[#8B5A2B]/40 mt-2">该赛季尚未评选</p>
          </div>
        )}
      </section>

      {/* 赛季数据之王 */}
      <section >
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1 h-5 bg-[#1F5F43]" />
          <h3 className="text-lg font-bold text-[#173126]">赛季数据之王</h3>
        </div>
        <DataKingsRow
          goldenBoot={awards?.golden_boot}
          playmaker={awards?.playmaker}
          goldenGlove={awards?.golden_glove}
          goldenWall={awards?.golden_wall}
          size="lg"
        />
      </section>

      {/* 全服年度最佳位置 */}
      <section >
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1 h-5 bg-[#B9EF3F]" />
          <h3 className="text-lg font-bold text-[#173126]">全服年度最佳位置</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <AwardCard award={awards?.best_fw} size="lg" />
          <AwardCard award={awards?.best_mf} size="lg" />
          <AwardCard award={awards?.best_df} size="lg" />
          <AwardCard award={awards?.best_gk} size="lg" />
        </div>
      </section>

      {/* 各联赛最佳阵容 */}
      {activeLeagueAwards.length > 0 && (
        <section >
          <div className="flex items-center gap-2 mb-4">
            <div className="w-1 h-5 bg-[#FFC247]" />
            <h3 className="text-lg font-bold text-[#173126]">各联赛最佳阵容</h3>
            <span className="text-xs text-[#8B5A2B]/40">({activeLeagueAwards.length} 个联赛)</span>
          </div>
          <div className="space-y-6">
            {activeLeagueAwards.map((la) => (
              <div key={la.league_id} className="border border-[#1F5F43]/20 bg-[#ECFFD8] overflow-hidden">
                <div className="px-4 py-2.5 bg-[#FFF8DC]/80 border-b border-[#1F5F43]/20 flex items-center justify-between">
                  <span className="text-sm font-bold text-[#173126]">联赛最佳阵容</span>
                  <span className="text-xs text-[#8B5A2B]/40">第 {la.season_number} 赛季</span>
                </div>
                <div className="p-4">
                  <TeamOfSeasonGrid team={la.team_of_season} />
                  {la.golden_boot && (
                    <div className="mt-4 pt-4 border-t border-[#1F5F43]/20">
                      <div className="text-xs text-[#466353] mb-2">联赛数据之王</div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                        <AwardCard award={la.golden_boot} size="sm" showMetadata={false} />
                        <AwardCard award={la.playmaker} size="sm" showMetadata={false} />
                        <AwardCard award={la.golden_glove} size="sm" showMetadata={false} />
                        <AwardCard award={la.golden_wall} size="sm" showMetadata={false} />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function WorldPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<WorldTab>('rankings')
  const [playerPosition, setPlayerPosition] = useState<PlayerPosition>('ALL')
  const [sortType, setSortType] = useState<WorldSortType>('ovr')
  const [teamSortType, setTeamSortType] = useState<WorldTeamSortType>('ranking')

  const isTeamRanking = teamSortType === 'ranking'
  const { rankings, loading: rankingsLoading } = useWorldRankings()
  const { items: teamLbItems, loading: teamLbLoading } = useWorldTeamLeaderboard(
    isTeamRanking ? null : teamSortType,
    100
  )
  const teamSortOption = TEAM_SORT_OPTIONS.find(o => o.value === teamSortType)

  const { players: ovrPlayers, loading: ovrLoading } = useTopPlayers(
    100,
    playerPosition === 'ALL' ? undefined : playerPosition
  )
  const { items: lbItems, loading: lbLoading } = useWorldLeaderboard(
    sortType === 'ovr' ? 'goals' : sortType,
    100,
    playerPosition === 'ALL' ? undefined : playerPosition
  )

  const isOvrSort = sortType === 'ovr'
  const players = isOvrSort ? ovrPlayers : lbItems
  const playersLoading = isOvrSort ? ovrLoading : lbLoading
  const sortOption = WORLD_SORT_OPTIONS.find(o => o.value === sortType)

  return (
    <div className="max-w-[1200px]">
      <button
        onClick={() => navigate(-1)}
        className="text-sm text-[#466353] hover:text-[#173126] transition-colors mb-4"
      >
        返回上一页
      </button>
      <PageHeader
        title="世界排名"
        subtitle="全球球队、球员排名与世界纪录"
      />

      <SegmentedTabs
        tabs={TABS}
        value={activeTab}
        onChange={(v) => setActiveTab(v as WorldTab)}
      />

      {/* Tab 内容 */}
      <div className="space-y-6">
        {activeTab === 'rankings' && (
          <div >
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
              <div className="relative">
                <select
                  value={teamSortType}
                  onChange={(e) => setTeamSortType(e.target.value as WorldTeamSortType)}
                  className="appearance-none bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 text-[#173126] text-xs px-3 py-1 pr-7 focus:outline-none focus:border-[#1F5F43] cursor-pointer"
                >
                  {TEAM_SORT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
                <ChevronRight className="w-3 h-3 text-[#466353] absolute right-2 top-1/2 -translate-y-1/2 rotate-90 pointer-events-none" />
              </div>
            </div>
            {isTeamRanking ? (
              rankingsLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="h-12 bg-[#FFF8DC]/80 animate-pulse" />
                  ))}
                </div>
              ) : rankings.length === 0 ? (
                <div className="text-center py-12">

                  <p className="text-[#466353]">暂无排名数据</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-xs text-[#466353] border-b border-[#1F5F43]/20">
                        <th className="py-2 px-4 font-medium">排名</th>
                        <th className="py-2 px-4 font-medium">球队</th>
                        <th className="py-2 px-4 font-medium text-center">
                          <span className="inline-flex items-center gap-1">
                            联赛积分
                            <span title="联赛积分 = 近3赛季联赛积分 × 联赛权重（超级×10 / 甲级×5 / 乙级×2.5 / 丙级×1）">
                              <InfoBox className="w-3.5 h-3.5 text-[#8B5A2B]/40 hover:text-[#1F5F43] cursor-help" />
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
              )
            ) : (
              teamLbLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="h-12 bg-[#FFF8DC]/80 animate-pulse" />
                  ))}
                </div>
              ) : teamLbItems.length === 0 ? (
                <div className="text-center py-12">

                  <p className="text-[#466353]">暂无排名数据</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-xs text-[#466353] border-b border-[#1F5F43]/20">
                        <th className="py-2 px-4 font-medium">排名</th>
                        <th className="py-2 px-4 font-medium">球队</th>
                        <th className="py-2 px-4 font-medium text-center">场次</th>
                        <th className="py-2 px-4 font-medium text-center">
                          {teamSortOption?.label ?? '数值'}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {teamLbItems.map((item) => (
                        <TeamLeaderboardRow
                          key={item.team_id}
                          item={item}
                          format={teamSortOption?.format ?? 'int'}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            )}
          </div>
        )}

        {activeTab === 'players' && (
          <div >
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
              <h3 className="text-lg font-semibold">球员排名</h3>
              <div className="flex flex-wrap gap-2 items-center">
                <div className="flex gap-1">
                  {POSITION_FILTERS.map((filter) => (
                    <button
                      key={filter.value}
                      onClick={() => setPlayerPosition(filter.value)}
                      className={clsx(
                        'px-3 py-1 text-xs font-medium border-2 transition-all',
                        playerPosition === filter.value
                          ? 'bg-[#B9EF3F] text-[#173126] border-[#1F5F43]'
                          : 'bg-[#FFF8DC]/80 text-[#466353] border-[#1F5F43]/20 hover:border-[#1F5F43]'
                      )}
                    >
                      {filter.label}
                    </button>
                  ))}
                </div>
                <div className="relative">
                  <select
                    value={sortType}
                    onChange={(e) => setSortType(e.target.value as WorldSortType)}
                    className="appearance-none bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 text-[#173126] text-xs px-3 py-1 pr-7 focus:outline-none focus:border-[#1F5F43] cursor-pointer"
                  >
                    {WORLD_SORT_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                  <ChevronRight className="w-3 h-3 text-[#466353] absolute right-2 top-1/2 -translate-y-1/2 rotate-90 pointer-events-none" />
                </div>
              </div>
            </div>
            {playersLoading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="h-14 bg-[#FFF8DC]/80 animate-pulse" />
                ))}
              </div>
            ) : players.length === 0 ? (
              <div className="text-center py-12">

                <p className="text-[#466353]">暂无球员数据</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-xs text-[#466353] border-b border-[#1F5F43]/20">
                      <th className="py-2 px-4 font-medium">排名</th>
                      <th className="py-2 px-4 font-medium">球员</th>
                      <th className="py-2 px-4 font-medium">位置</th>
                      <th className="py-2 px-4 font-medium text-center">
                        {isOvrSort ? '年龄' : '场次'}
                      </th>
                      <th className="py-2 px-4 font-medium text-center">
                        {sortOption?.label ?? 'OVR'}
                      </th>
                      <th className="py-2 px-4 font-medium">球队</th>
                    </tr>
                  </thead>
                  <tbody>
                    {isOvrSort
                      ? (players as TopPlayer[]).map((player) => (
                          <PlayerRow key={player.player_id} player={player} />
                        ))
                      : (players as LeaderboardItem[]).map((item) => (
                          <LeaderboardPlayerRow
                            key={item.player_id}
                            item={item}
                            format={sortOption?.format ?? 'int'}
                          />
                        ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'records' && (
          <div >
            <WorldRecordsTab />
          </div>
        )}
        {activeTab === 'awards' && <WorldAwardsTab />}
      </div>
    </div>
  )
}

export default WorldPage
