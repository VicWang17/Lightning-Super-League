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
  RECORD_SCOPE_LABELS,
  RECORD_CATEGORY_LABELS,
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

  const currentRecords = records ? records[activeCategory] : []

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
        {CATEGORY_TABS.map((tab) => (
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
            {records && (
              <span className="ml-1.5 text-xs opacity-60">
                ({records[tab.value].length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* 纪录列表 */}
      {loading ? (
        <div className="text-center py-16 text-[#8B8BA7]">加载中...</div>
      ) : currentRecords.length === 0 ? (
        <div className="text-center py-16">
          <Crown className="w-12 h-12 text-[#2D2D44] mx-auto mb-4" />
          <p className="text-[#8B8BA7]">暂无{RECORD_CATEGORY_LABELS[activeCategory]}</p>
          <p className="text-xs text-[#4B4B6A] mt-1">随着比赛进行，纪录将自动生成</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {currentRecords.map((record) => (
            <RecordCard key={record.id} record={record} />
          ))}
        </div>
      )}
    </div>
  )
}

export default RecordsPage
