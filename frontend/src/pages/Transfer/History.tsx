import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import {
  Transfer,
  TrendingUp,
  TrendingDown,
  Loader,
  ChevronLeft,
  ChevronRight,
} from '../../components/ui/pixel-icons'
import api from '../../api/client'
import type { TransferRecordItem } from '../../types/transfer'
import { TRANSFER_TYPE_NAMES } from '../../types/transfer'

const navTabs = [
  { id: 'market', label: '拍卖市场', to: '/transfer/market' },
  { id: 'free', label: '自由市场', to: '/transfer/free-market' },
  { id: 'watchlist', label: '我的关注', to: '/transfer/watchlist' },
  { id: 'my-listings', label: '我的挂牌', to: '/transfer/my-listings' },
  { id: 'public-offers', label: '公开报价', to: '/transfer/public-offers' },
  { id: 'my-offers', label: '我的报价', to: '/transfer/my-offers' },
  { id: 'history', label: '转会历史', to: '/transfer/history' },
]

export default function TransferHistory() {
  const [records, setRecords] = useState<TransferRecordItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [teamId, setTeamId] = useState<string | null>(null)

  useEffect(() => {
    api.get<{ id: string }>('/teams/my-team').then(res => {
      if (res.success && res.data) setTeamId(res.data.id)
    })
  }, [])

  const fetchHistory = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: { team_id?: string; page: number; page_size: number } = { page, page_size: 20 }
      if (teamId) params.team_id = teamId
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
  }, [teamId, page])

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
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">转会市场</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">转会历史记录</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-b-2 border-[#2D2D44]">
        {navTabs.map((tab) => (
          <Link
            key={tab.id}
            to={tab.to}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-0.5',
              tab.id === 'history'
                ? 'border-[#0D7377] text-[#0D7377]'
                : 'border-transparent text-[#4B4B6A] hover:text-[#8B8BA7]'
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown className="w-4 h-4 text-red-400" />
            <span className="text-sm text-[#8B8BA7]">总支出</span>
          </div>
          <p className="text-2xl font-bold text-red-400 stat-number">{totalIn}万</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-[#8B8BA7]">总收入</span>
          </div>
          <p className="text-2xl font-bold text-emerald-400 stat-number">{totalOut}万</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Transfer className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">净投入</span>
          </div>
          <p className={clsx('text-2xl font-bold stat-number', totalIn - totalOut > 0 ? 'text-red-400' : 'text-emerald-400')}>
            {totalIn - totalOut > 0 ? '+' : ''}{totalIn - totalOut}万
          </p>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader className="w-6 h-6 text-[#0D7377] animate-spin" />
          <span className="ml-2 text-sm text-[#8B8BA7]">加载中...</span>
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-sm">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">转会记录</h3>
            <div className="space-y-3">
              {records.map((r) => {
                const isIn = r.to_team_id === teamId
                const isOut = r.from_team_id === teamId
                return (
                  <div key={r.record_id} className="flex items-center gap-4 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                    <div className={clsx(
                      'w-8 h-8 flex items-center justify-center border-2 text-xs font-bold',
                      isIn ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400' :
                      isOut ? 'bg-red-500/20 border-red-500/30 text-red-400' :
                      'bg-[#2D2D44] text-[#8B8BA7]'
                    )}>
                      {isIn ? '入' : isOut ? '出' : '—'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white">
                        <Link to={`/players/${r.player_id}`} className="hover:text-[#0D7377] transition-colors">
                          {r.player_name}
                        </Link>
                      </p>
                      <p className="text-xs text-[#4B4B6A]">
                        {TRANSFER_TYPE_NAMES[r.transfer_type]}
                        {r.from_team_id && r.to_team_id && ` · ${r.from_team_id.slice(0, 6)} → ${r.to_team_id.slice(0, 6)}`}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className={clsx('text-sm font-bold', isIn ? 'text-red-400' : isOut ? 'text-emerald-400' : 'text-[#8B8BA7]')}>
                        {isIn ? '-' : isOut ? '+' : ''}{r.amount}万
                      </p>
                      <p className="text-xs text-[#4B4B6A]">
                        {new Date(r.completed_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )
              })}
              {records.length === 0 && (
                <div className="text-center py-12 text-[#8B8BA7]">
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
                className="p-2 bg-[#12121A] border-2 border-[#2D2D44] text-[#8B8BA7] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-[#8B8BA7]">第 {page} / {totalPages} 页</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2 bg-[#12121A] border-2 border-[#2D2D44] text-[#8B8BA7] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
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
