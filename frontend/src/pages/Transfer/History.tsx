import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  ChevronLeft,
  ChevronRight,
} from '../../components/ui/pixel-icons'
import Avatar from '../../components/ui/Avatar'
import api from '../../api/client'
import type { TransferRecordItem } from '../../types/transfer'
import { TRANSFER_TYPE_NAMES } from '../../types/transfer'
import { TransferTabs } from '../../components/transfer/TransferTabs'
import { PageHeader } from '../../components/ui/PageHeader'

interface TransferHistoryProps {
  embedded?: boolean
}

export default function TransferHistory({ embedded }: TransferHistoryProps = {}) {
  const [records, setRecords] = useState<TransferRecordItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [teamId, setTeamId] = useState<string | null>(null)

  useEffect(() => {
    if (embedded) return
    api.get<{ id: string }>('/teams/my-team').then(res => {
      if (res.success && res.data) setTeamId(res.data.id)
    })
  }, [embedded])

  const fetchHistory = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: { team_id?: string; page: number; page_size: number } = { page, page_size: 20 }
      if (!embedded && teamId) params.team_id = teamId
      const res = await api.getTransferHistory(params)
      if (res.success && res.data) {
        setRecords(res.data.items)
        setTotalPages(res.data.total_pages)
      } else {
        setRecords([])
        setTotalPages(1)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取数据失败')
    } finally {
      setLoading(false)
    }
  }, [teamId, page, embedded])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  // Stats - filter by my team
  const myRecords = teamId
    ? records.filter(r => r.from_team_id === teamId || r.to_team_id === teamId)
    : records

  const totalIn = myRecords.filter(r => r.to_team_id === teamId).reduce((s, r) => s + r.amount, 0)
  const totalOut = myRecords.filter(r => r.from_team_id === teamId).reduce((s, r) => s + r.amount, 0)

  return (
    <div className={embedded ? 'space-y-4' : 'space-y-6 max-w-[1400px]'}>
      {!embedded && (
        <>
          <PageHeader title="转会历史" subtitle="转会历史记录" />

          <TransferTabs />
        </>
      )}

      {/* Stats */}
      {!embedded && (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="mb-2">
            <span className="text-sm text-[#466353]">总支出</span>
          </div>
          <p className="text-2xl font-bold text-[#FF6F59] stat-number">{(totalIn / 10000).toFixed(1)}万</p>
        </div>
        <div className="card">
          <div className="mb-2">
            <span className="text-sm text-[#466353]">总收入</span>
          </div>
          <p className="text-2xl font-bold text-[#1F5F43] stat-number">{(totalOut / 10000).toFixed(1)}万</p>
        </div>
        <div className="card">
          <div className="mb-2">
            <span className="text-sm text-[#466353]">净投入</span>
          </div>
          <p className={clsx('text-2xl font-bold stat-number', totalIn - totalOut > 0 ? 'text-[#FF6F59]' : 'text-[#1F5F43]')}>
            {totalIn - totalOut > 0 ? '+' : ''}{((totalIn - totalOut) / 10000).toFixed(1)}万
          </p>
        </div>
      </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-12 text-sm text-[#466353]">
          加载中...
        </div>
      )}
      {error && (
        <div className="p-4 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30 text-[#FF6F59] text-sm">
          {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">转会记录</h3>
            <div className="space-y-2">
              <div
                className="fresh-roster-row text-[10px] font-black text-[#466353] uppercase tracking-wider opacity-80 pointer-events-none"
                style={{ gridTemplateColumns: '56px minmax(0, 1fr) minmax(0, 1fr) 120px 100px' }}
              >
                <span className="text-center">头像</span>
                <span className="px-2">球员</span>
                <span className="px-2">转会流向</span>
                <span className="text-right px-2">金额</span>
                <span className="text-right px-2">日期</span>
              </div>

              {records.map((r) => {
                const isIn = r.to_team_id === teamId
                const isOut = r.from_team_id === teamId

                let flowText = ''
                if (r.transfer_type === 'renewal') {
                  flowText = `${r.to_team_name || r.to_team_id.slice(0, 6)} 续约`
                } else if (r.transfer_type === 'free_market_signing') {
                  flowText = `自由球员 → ${r.to_team_name || r.to_team_id.slice(0, 6)}`
                } else if (r.transfer_type === 'release') {
                  flowText = `${r.from_team_name || r.from_team_id.slice(0, 6)} → 自由市场`
                } else {
                  flowText = `${r.from_team_name || r.from_team_id.slice(0, 6)} → ${r.to_team_name || r.to_team_id.slice(0, 6)}`
                }

                return (
                  <div
                    key={r.record_id}
                    className="fresh-roster-row group"
                    style={{ gridTemplateColumns: '56px minmax(0, 1fr) minmax(0, 1fr) 120px 100px' }}
                  >
                    <Avatar src={r.avatar_url} name={r.player_name} size="lg" />

                    <div className="min-w-0 px-2 overflow-hidden">
                      <p className="text-sm font-medium text-[#173126] truncate">
                        <Link to={`/players/${r.player_id}`} className="hover:text-[#1F5F43] transition-colors">
                          {r.player_name}
                        </Link>
                      </p>
                      <p className="text-xs text-[#466353]">
                        {TRANSFER_TYPE_NAMES[r.transfer_type]}
                      </p>
                    </div>

                    <div className="min-w-0 px-2 overflow-hidden flex items-center">
                      <span className="text-sm text-[#173126] truncate">{flowText}</span>
                    </div>

                    <div className="text-right">
                      <p className={clsx('text-sm font-bold', isIn ? 'text-[#FF6F59]' : isOut ? 'text-[#1F5F43]' : 'text-[#466353]')}>
                        {isIn ? '-' : isOut ? '+' : ''}{(r.amount / 10000).toFixed(1)}万
                      </p>
                    </div>

                    <div className="text-right">
                      <p className="text-xs text-[#466353]">
                        {new Date(r.completed_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )
              })}
              {records.length === 0 && (
                <div className="text-center py-12 text-[#466353]">
                  <p className="text-sm">暂无转会记录</p>
                </div>
              )}
            </div>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 bg-[#FFF8DC] border-2 border-[#1F5F43]/20 text-[#466353] hover:border-[#1F5F43] hover:text-[#173126] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-[#466353]">第 {page} / {totalPages} 页</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2 bg-[#FFF8DC] border-2 border-[#1F5F43]/20 text-[#466353] hover:border-[#1F5F43] hover:text-[#173126] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
