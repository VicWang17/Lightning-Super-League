import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import { Crown, ChevronRight } from '../../components/ui/pixel-icons'
import { Card } from '../../components/ui/Card'
import { api } from '../../api/client'
import {
  type RecordItem,
  type RecordsByCategory,
  RecordScope,
  RecordCategory,
  RecordType,
  RECORD_SCOPE_LABELS,
  RECORD_CATEGORY_LABELS,
  RECORD_TYPE_LABELS,
  RECORD_TYPES_BY_CATEGORY,
} from '../../types/records'

const SCOPE_TABS = [
  { value: RecordScope.WORLD, label: RECORD_SCOPE_LABELS[RecordScope.WORLD] },
  { value: RecordScope.LEAGUE, label: RECORD_SCOPE_LABELS[RecordScope.LEAGUE] },
  { value: RecordScope.TEAM, label: RECORD_SCOPE_LABELS[RecordScope.TEAM] },
]

const CATEGORY_TABS = [
  { value: RecordCategory.TEAM, label: RECORD_CATEGORY_LABELS[RecordCategory.TEAM] },
  { value: RecordCategory.PLAYER, label: RECORD_CATEGORY_LABELS[RecordCategory.PLAYER] },
  { value: RecordCategory.MATCH, label: RECORD_CATEGORY_LABELS[RecordCategory.MATCH] },
]

function RecordCard({ record }: { record: RecordItem }) {
  const isPlayerRecord = record.category === RecordCategory.PLAYER

  return (
    <Card className="bg-[#12121A] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 transition-all">
      <div className="flex items-start gap-4">
        {/* 图标/头像 */}
        <div className="shrink-0">
          {isPlayerRecord && record.holder_avatar_url ? (
            <div className="w-12 h-12 bg-[#1E1E2D] border-2 border-[#2D2D44] overflow-hidden">
              <img
                src={`/${record.holder_avatar_url}`}
                alt={record.holder_name}
                className="w-full h-full object-cover"
              />
            </div>
          ) : (
            <div className="w-12 h-12 bg-[#0D4A4D]/30 border-2 border-[#0D7377]/30 flex items-center justify-center">
              <Crown className="w-6 h-6 text-[#0D7377]" />
            </div>
          )}
        </div>

        {/* 内容 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-white truncate">
              {record.record_type_label}
            </h3>
            <span className="text-lg font-bold stat-number pixel-number text-[#C6F135]">
              {record.record_value}
            </span>
          </div>

          <div className="mt-1 flex items-center gap-2 text-sm">
            <span className="text-white font-medium">{record.holder_name}</span>
            {record.holder_team_name && (
              <span className="text-[#8B8BA7]">· {record.holder_team_name}</span>
            )}
          </div>

          <div className="mt-2 flex items-center gap-3 text-xs text-[#4B4B6A]">
            {record.season_number !== undefined && (
              <span>第 {record.season_number} 赛季</span>
            )}
            {record.match_date && (
              <span>{record.match_date}</span>
            )}
            {record.fixture_id && (
              <Link
                to={`/match/${record.fixture_id}`}
                className="inline-flex items-center gap-0.5 text-[#0D7377] hover:text-[#C6F135] transition-colors"
              >
                查看比赛
                <ChevronRight className="w-3 h-3" />
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
            <Crown className="w-6 h-6 text-[#0D7377]/50" />
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-[#8B8BA7] truncate">
              {RECORD_TYPE_LABELS[recordType]}
            </h3>
            <span className="text-lg font-bold stat-number pixel-number text-[#4B4B6A]">
              —
            </span>
          </div>

          <div className="mt-1 text-sm text-[#4B4B6A]">
            暂无该纪录
          </div>
        </div>
      </div>
    </Card>
  )
}

function RecordsPage() {
  const [scope, setScope] = useState<RecordScope>(RecordScope.WORLD)
  const [activeCategory, setActiveCategory] = useState<RecordCategory>(RecordCategory.PLAYER)
  const [records, setRecords] = useState<RecordsByCategory | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    async function fetchRecords() {
      setLoading(true)
      try {
        const params = new URLSearchParams()
        params.append('scope', scope)

        // 联赛/队伍纪录需要传入对应的 scope_target_id
        if (scope !== RecordScope.WORLD) {
          const teamRes = await api.get<{
            id: string
            league_id?: string
          }>('/teams/my-team')
          if (teamRes.success) {
            const targetId =
              scope === RecordScope.LEAGUE
                ? teamRes.data.league_id
                : teamRes.data.id
            if (targetId) {
              params.append('scope_target_id', targetId)
            }
          }
        }

        const res = await api.get<RecordsByCategory>(`/records?${params.toString()}`)
        if (res.success) {
          setRecords(res.data)
        }
      } catch (err) {
        console.error('Failed to fetch records:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchRecords()
  }, [scope])

  // 按 record_type 索引后端数据
  const recordsByType = new Map<RecordType, RecordItem>()
  if (records) {
    records[activeCategory].forEach((r) => recordsByType.set(r.record_type, r))
  }

  // 当前分类下所有应该显示的纪录类型
  const allRecordTypes = RECORD_TYPES_BY_CATEGORY[activeCategory]

  return (
    <div className="max-w-[1200px]">
      {/* 页面标题 */}
      <div className="flex items-center gap-3 mb-6">
        <Crown className="w-7 h-7 text-[#C6F135]" />
        <h1 className="text-2xl font-bold pixel-title">纪录中心</h1>
      </div>

      {/* Scope 选择器 */}
      <div className="flex gap-2 mb-6">
        {SCOPE_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setScope(tab.value)}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-2 transition-all',
              scope === tab.value
                ? 'bg-[#C6F135] text-[#0A0A0F] border-[#C6F135]'
                : 'bg-[#12121A] text-[#8B8BA7] border-[#2D2D44] hover:border-[#0D7377] hover:text-white'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Category Tab */}
      <div className="flex gap-1 mb-6 border-b-2 border-[#2D2D44]">
        {CATEGORY_TABS.map((tab) => {
          const total = RECORD_TYPES_BY_CATEGORY[tab.value].length
          const has = records ? records[tab.value].length : 0
          return (
            <button
              key={tab.value}
              onClick={() => setActiveCategory(tab.value)}
              className={clsx(
                'px-4 py-2.5 text-sm font-medium border-b-2 -mb-0.5 transition-all',
                activeCategory === tab.value
                  ? 'border-[#C6F135] text-[#C6F135]'
                  : 'border-transparent text-[#8B8BA7] hover:text-white'
              )}
            >
              {tab.label}
              <span className="ml-1.5 text-xs opacity-60">
                ({has}/{total})
              </span>
            </button>
          )
        })}
      </div>

      {/* 纪录列表 */}
      {loading ? (
        <div className="text-center py-16 text-[#8B8BA7]">加载中...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {allRecordTypes.map((type) => {
            const record = recordsByType.get(type)
            return record ? (
              <RecordCard key={type} record={record} />
            ) : (
              <EmptyRecordCard key={type} recordType={type} />
            )
          })}
        </div>
      )}
    </div>
  )
}

export default RecordsPage
