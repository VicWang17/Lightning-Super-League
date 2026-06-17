import { useMemo, useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import Avatar from '../ui/Avatar'
import {
  User,
  Users,
  Sword,
  ExternalLink,
  Target,
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

const CATEGORY_ICONS: Record<RecordCategory, typeof User> = {
  [RecordCategory.PLAYER]: User,
  [RecordCategory.TEAM]: Users,
  [RecordCategory.MATCH]: Sword,
}

const CATEGORY_ACCENT: Record<RecordCategory, string> = {
  [RecordCategory.PLAYER]: 'text-[#0D7377] bg-[#0D4A4D]/30 border-[#0D7377]/30',
  [RecordCategory.TEAM]: 'text-[#3B82F6] bg-[#1E3A8A]/20 border-[#3B82F6]/30',
  [RecordCategory.MATCH]: 'text-[#D6A619] bg-[#3D2A1A]/40 border-[#D6A619]/30',
}

function RecordAvatar({ record }: { record: RecordItem }) {
  if (record.category === RecordCategory.PLAYER) {
    return (
      <Avatar
        src={record.holder_avatar_url ? `/${record.holder_avatar_url}` : undefined}
        name={record.holder_name}
        size="sm"
        fallback={<User className="w-4 h-4 text-[#8B8BA7]" />}
        className="border-[#2D2D44]"
      />
    )
  }

  const Icon = record.category === RecordCategory.MATCH ? Sword : Users
  return (
    <div
      className={clsx(
        'w-9 h-9 border-2 flex items-center justify-center shrink-0',
        CATEGORY_ACCENT[record.category]
      )}
    >
      <Icon className="w-4 h-4" />
    </div>
  )
}

function RecordMeta({ record }: { record: RecordItem }) {
  return (
    <div className="flex items-center gap-2 text-[10px] sm:text-xs text-[#4B4B6A]">
      {record.season_number !== undefined && (
        <span className="px-1 py-0.5 bg-[#1E1E2D] border border-[#2D2D44]">
          第 {record.season_number} 赛季
        </span>
      )}
      {record.match_date && <span>{record.match_date}</span>}
      {record.fixture_id && (
        <Link
          to={`/match/${record.fixture_id}`}
          className="inline-flex items-center gap-0.5 text-[#0D7377] hover:text-[#C6F135] transition-colors"
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
    <div className="group flex items-center gap-3 px-3 py-2.5 bg-[#12121A] border border-[#2D2D44]/60 hover:border-[#0D7377]/50 hover:bg-[#1A1A26] transition-all">
      <RecordAvatar record={record} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-[#8B8BA7]">
            {record.record_type_label}
          </span>
          <RecordMeta record={record} />
        </div>

        <div className="mt-0.5 flex items-center gap-1.5 text-sm min-w-0">
          <Link
            to={holderLink}
            className="font-semibold text-white hover:text-[#C6F135] truncate transition-colors"
          >
            {record.holder_name}
          </Link>
          {record.category === RecordCategory.PLAYER && record.holder_team_name && (
            <>
              <span className="text-[#4B4B6A]">·</span>
              <Link
                to={`/teams/${record.holder_team_id}`}
                className="text-[#8B8BA7] hover:text-white truncate transition-colors"
              >
                {record.holder_team_name}
              </Link>
            </>
          )}
        </div>
      </div>

      <div className="shrink-0 text-right pl-2">
        <div className="text-base sm:text-lg font-bold stat-number pixel-number text-[#C6F135] leading-none">
          {record.record_value}
        </div>
      </div>
    </div>
  )
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="text-center py-12 border border-dashed border-[#2D2D44]/60 bg-[#12121A]/50">
      <Target className="w-10 h-10 text-[#4B4B6A] mx-auto mb-3" />
      <p className="text-[#8B8BA7] text-sm">{text}</p>
    </div>
  )
}

function SkeletonRows() {
  return (
    <div className="space-y-1.5 animate-pulse">
      {[1, 2, 3, 4, 5].map((i) => (
        <div
          key={i}
          className="flex items-center gap-3 px-3 py-3 bg-[#12121A] border border-[#2D2D44]/60"
        >
          <div className="w-9 h-9 bg-[#1E1E2D]" />
          <div className="flex-1 space-y-2">
            <div className="h-3 bg-[#1E1E2D] w-1/3" />
            <div className="h-3 bg-[#1E1E2D] w-1/2" />
          </div>
          <div className="w-16 h-5 bg-[#1E1E2D]" />
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
        <div className="flex gap-1 border-b-2 border-[#2D2D44]">
          {categories.map((cat) => {
            const Icon = CATEGORY_ICONS[cat]
            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={clsx(
                  'flex items-center gap-1.5 px-3 py-2 text-xs sm:text-sm font-medium border-b-2 -mb-0.5 transition-all',
                  activeCategory === cat
                    ? 'border-[#C6F135] text-[#C6F135]'
                    : 'border-transparent text-[#8B8BA7] hover:text-white'
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {RECORD_CATEGORY_LABELS[cat]}
                <span className="ml-1 text-[10px] opacity-60">
                  {records[cat].length}
                </span>
              </button>
            )
          })}
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
