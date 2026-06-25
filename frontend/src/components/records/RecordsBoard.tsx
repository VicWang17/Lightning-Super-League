import { useMemo, useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import Avatar from '../ui/Avatar'
import {
  User,
  ExternalLink,
} from '../../components/ui/pixel-icons'
import {
  RecordCategory,
  RECORD_CATEGORY_LABELS,
  RECORD_TYPES_BY_CATEGORY,
  type RecordItem,
  type RecordsByCategory,
} from '../../types/records'

export interface RecordsBoardProps {
  records: RecordsByCategory | null
  loading?: boolean
  emptyText?: string
}

function RecordAvatar({ record }: { record: RecordItem }) {
  if (record.category !== RecordCategory.PLAYER) return null

  return (
    <Avatar
      src={record.holder_avatar_url ? `/${record.holder_avatar_url}` : undefined}
      name={record.holder_name}
      size="sm"
      fallback={<User className="w-4 h-4 text-[#466353]" />}
      className="border-[#1F5F43]/20"
    />
  )
}

function RecordMeta({ record }: { record: RecordItem }) {
  return (
    <div className="flex items-center gap-2 text-[10px] sm:text-xs text-[#8B5A2B]/40">
      {record.season_number !== undefined && (
        <span className="px-1 py-0.5 bg-[#FFF8DC]/80 border border-[#1F5F43]/20">
          第 {record.season_number} 赛季
        </span>
      )}
      {record.match_date && <span>{record.match_date}</span>}
      {record.fixture_id && (
        <Link
          to={`/match/${record.fixture_id}`}
          className="inline-flex items-center gap-0.5 text-[#1F5F43] hover:text-[#1F5F43] transition-colors"
        >
          比赛
          <ExternalLink className="w-3 h-3" />
        </Link>
      )}
    </div>
  )
}

function RecordRow({ record }: { record: RecordItem }) {
  const holderLink =
    record.category === RecordCategory.PLAYER
      ? `/players/${record.holder_id}`
      : `/teams/${record.holder_id}`

  return (
    <div className="group flex items-center gap-3 px-3 py-2.5 bg-[#FFF8DC]/80 border border-[#1F5F43]/20 hover:border-[#1F5F43] hover:bg-[#FFF8DC]/60 transition-all">
      <RecordAvatar record={record} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-[#466353]">
            {record.record_type_label}
          </span>
          <RecordMeta record={record} />
        </div>

        <div className="mt-0.5 flex items-center gap-1.5 text-sm min-w-0">
          <Link
            to={holderLink}
            className="font-semibold text-[#173126] hover:text-[#1F5F43] truncate transition-colors"
          >
            {record.holder_name}
          </Link>
          {record.category === RecordCategory.PLAYER && record.holder_team_name && (
            <>
              <span className="text-[#8B5A2B]/40">·</span>
              <Link
                to={`/teams/${record.holder_team_id}`}
                className="text-[#466353] hover:text-[#173126] truncate transition-colors"
              >
                {record.holder_team_name}
              </Link>
            </>
          )}
        </div>
      </div>

      <div className="shrink-0 text-right pl-2">
        <div className="text-base sm:text-lg font-bold stat-number pixel-number text-[#1F5F43] leading-none">
          {record.record_value}
        </div>
      </div>
    </div>
  )
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="text-center py-12 border border-dashed border-[#1F5F43]/20 bg-[#FFF8DC]/80">
      <p className="text-[#466353] text-sm">{text}</p>
    </div>
  )
}

function SkeletonRows() {
  return (
    <div className="space-y-1.5 animate-pulse">
      {[1, 2, 3, 4, 5].map((i) => (
        <div
          key={i}
          className="flex items-center gap-3 px-3 py-3 bg-[#FFF8DC]/80 border border-[#1F5F43]/20"
        >
          <div className="w-9 h-9 bg-[#FFF8DC]/80" />
          <div className="flex-1 space-y-2">
            <div className="h-3 bg-[#FFF8DC]/80 w-1/3" />
            <div className="h-3 bg-[#FFF8DC]/80 w-1/2" />
          </div>
          <div className="w-16 h-5 bg-[#FFF8DC]/80" />
        </div>
      ))}
    </div>
  )
}

export function RecordsBoard({
  records,
  loading = false,
  emptyText = '暂无纪录',
}: RecordsBoardProps) {
  const categories = useMemo(() => {
    if (!records) return []
    const cats: RecordCategory[] = []
    if (records.player.length > 0) cats.push(RecordCategory.PLAYER)
    if (records.team.length > 0) cats.push(RecordCategory.TEAM)
    if (records.match.length > 0) cats.push(RecordCategory.MATCH)
    return cats
  }, [records])

  const [activeCategory, setActiveCategory] = useState<RecordCategory | null>(null)

  useEffect(() => {
    if (!activeCategory || !categories.includes(activeCategory)) {
      setActiveCategory(categories[0] ?? null)
    }
  }, [categories, activeCategory])

  if (loading) {
    return <SkeletonRows />
  }

  if (!records || categories.length === 0) {
    return <EmptyState text={emptyText} />
  }

  const activeRecords = activeCategory ? records[activeCategory] : []
  const orderedTypes = activeCategory ? RECORD_TYPES_BY_CATEGORY[activeCategory] : []

  return (
    <div className="space-y-3">
      {categories.length > 1 && (
        <div className="flex gap-1 border-b-2 border-[#1F5F43]/20">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-2 text-xs sm:text-sm font-medium border-b-2 -mb-0.5 transition-all',
                activeCategory === cat
                  ? 'border-[#B9EF3F] text-[#1F5F43]'
                  : 'border-transparent text-[#466353] hover:text-[#173126]'
              )}
            >
              {RECORD_CATEGORY_LABELS[cat]}
              <span className="ml-1 text-[10px] opacity-60">
                {records[cat].length}
              </span>
            </button>
          ))}
        </div>
      )}

      <div className="space-y-0.5">
        {orderedTypes.map((type) => {
          const record = activeRecords.find((r) => r.record_type === type)
          if (!record) return null
          return <RecordRow key={`${activeCategory}-${type}`} record={record} />
        })}
      </div>
    </div>
  )
}
