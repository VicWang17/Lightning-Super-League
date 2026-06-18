import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertTriangle, X } from 'lucide-react'
import {
  Search,
  Eye,
  Send,
  Loader,
  ChevronLeft,
  ChevronRight,
  Banknote,
  Target,
} from '../../components/ui/pixel-icons'
import { TransferTabs } from '../../components/transfer/TransferTabs'
import { PageHeader } from '../../components/ui/PageHeader'
import api from '../../api/client'
import type { MarketPlayer } from '../../types/transfer'
import { POSITION_COLORS } from '../../types/player'

const positionOptions = [
  { value: '', label: '全部位置' },
  { value: 'FW', label: '前锋' },
  { value: 'MF', label: '中场' },
  { value: 'DF', label: '后卫' },
  { value: 'GK', label: '门将' },
]

const ovrOptions = [
  { value: '', label: '全部能力' },
  { value: '60', label: '60+' },
  { value: '65', label: '65+' },
  { value: '70', label: '70+' },
  { value: '75', label: '75+' },
]

interface Filters {
  position: string
  min_ovr: string
  max_ovr: string
  min_age: string
  max_age: string
  is_listed: string
  search: string
}

export default function TransferMarket() {
  const navigate = useNavigate()
  const [players, setPlayers] = useState<MarketPlayer[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [filters, setFilters] = useState<Filters>({
    position: '',
    min_ovr: '',
    max_ovr: '',
    min_age: '',
    max_age: '',
    is_listed: '',
    search: '',
  })

  // Offer modal
  const [offerPlayer, setOfferPlayer] = useState<MarketPlayer | null>(null)
  const [offerAmount, setOfferAmount] = useState('')
  const [offerLoading, setOfferLoading] = useState(false)
  const [offerError, setOfferError] = useState<string | null>(null)
  const [offerSuccess, setOfferSuccess] = useState(false)

  const fetchPlayers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, unknown> = { page, page_size: 20 }
      if (filters.position) params.position = filters.position
      if (filters.min_ovr) params.min_ovr = Number(filters.min_ovr)
      if (filters.max_ovr) params.max_ovr = Number(filters.max_ovr)
      if (filters.min_age) params.min_age = Number(filters.min_age)
      if (filters.max_age) params.max_age = Number(filters.max_age)
      if (filters.is_listed) {
        params.is_listed = filters.is_listed === 'listed'
      }

      const res = await api.getTransferMarket(params)
      if (res.success && res.data) {
        let items = res.data.items
        if (filters.search) {
          const s = filters.search.toLowerCase()
          items = items.filter(p => p.name.toLowerCase().includes(s) || p.team_name.toLowerCase().includes(s))
        }
        setPlayers(items)
        setTotalPages(res.data.total_pages)
      } else {
        setPlayers([])
        setTotalPages(1)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取数据失败')
    } finally {
      setLoading(false)
    }
  }, [page, filters])

  useEffect(() => {
    fetchPlayers()
  }, [fetchPlayers])

  const handleFilterChange = (key: keyof Filters, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setPage(1)
  }

  const openOfferModal = (player: MarketPlayer) => {
    setOfferPlayer(player)
    setOfferAmount(player.list_price ? String(Math.round(player.list_price / 10000)) : String(Math.round(player.market_value / 10000)))
    setOfferError(null)
    setOfferSuccess(false)
  }

  const closeOfferModal = () => {
    setOfferPlayer(null)
    setOfferAmount('')
    setOfferError(null)
    setOfferSuccess(false)
  }

  const submitOffer = async () => {
    if (!offerPlayer || !offerAmount) return
    setOfferLoading(true)
    setOfferError(null)
    try {
      const teamRes = await api.get<{ id: string }>('/teams/my-team')
      if (!teamRes.success || !teamRes.data) {
        setOfferError('无法获取球队信息')
        setOfferLoading(false)
        return
      }
      const res = await api.createTransferOffer({
        player_id: offerPlayer.player_id,
        buyer_team_id: teamRes.data.id,
        amount: Number(offerAmount) * 10000,
        listing_id: offerPlayer.listing_id || undefined,
      })
      if (res.success && res.data) {
        setOfferSuccess(true)
      } else {
        setOfferError(res.message || '报价失败')
      }
    } catch (err) {
      setOfferError(err instanceof Error ? err.message : '报价请求失败')
    } finally {
      setOfferLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors mb-4"
      >
        <ChevronLeft className="w-4 h-4" />
        返回上一页
      </button>
      <PageHeader icon={Target} title="球员拍卖市场" subtitle="浏览球员并发送转会报价" />

      <TransferTabs />

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#4B4B6A]" />
          <input
            type="text"
            placeholder="搜索球员或球队..."
            value={filters.search}
            onChange={e => handleFilterChange('search', e.target.value)}
            className="w-full bg-[#12121A] border-2 border-[#2D2D44] pl-10 pr-4 py-2 text-sm text-[#E2E2F0] placeholder:text-[#4B4B6A] focus:outline-none focus:border-[#0D7377]/50"
          />
        </div>
        <select
          value={filters.position}
          onChange={e => handleFilterChange('position', e.target.value)}
          className="bg-[#12121A] border-2 border-[#2D2D44] px-3 py-2 text-sm text-[#E2E2F0] focus:outline-none focus:border-[#0D7377]/50"
        >
          {positionOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select
          value={filters.min_ovr}
          onChange={e => handleFilterChange('min_ovr', e.target.value)}
          className="bg-[#12121A] border-2 border-[#2D2D44] px-3 py-2 text-sm text-[#E2E2F0] focus:outline-none focus:border-[#0D7377]/50"
        >
          {ovrOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <input
          type="number"
          placeholder="最低年龄"
          value={filters.min_age}
          onChange={e => handleFilterChange('min_age', e.target.value)}
          className="w-24 bg-[#12121A] border-2 border-[#2D2D44] px-3 py-2 text-sm text-[#E2E2F0] placeholder:text-[#4B4B6A] focus:outline-none focus:border-[#0D7377]/50"
        />
        <input
          type="number"
          placeholder="最高年龄"
          value={filters.max_age}
          onChange={e => handleFilterChange('max_age', e.target.value)}
          className="w-24 bg-[#12121A] border-2 border-[#2D2D44] px-3 py-2 text-sm text-[#E2E2F0] placeholder:text-[#4B4B6A] focus:outline-none focus:border-[#0D7377]/50"
        />
        <select
          value={filters.is_listed}
          onChange={e => handleFilterChange('is_listed', e.target.value)}
          className="bg-[#12121A] border-2 border-[#2D2D44] px-3 py-2 text-sm text-[#E2E2F0] focus:outline-none focus:border-[#0D7377]/50"
        >
          <option value="">全部状态</option>
          <option value="listed">仅挂牌</option>
          <option value="unlisted">未挂牌</option>
        </select>
      </div>

      {/* Loading & Error */}
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

      {/* Table */}
      {!loading && !error && (
        <>
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">球员列表</h3>
              <span className="text-xs text-[#4B4B6A]">共 {players.length} 名球员</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b-2 border-[#2D2D44]">
                    <th className="text-left text-xs text-[#4B4B6A] pb-2 font-medium">球员</th>
                    <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">位置</th>
                    <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">年龄</th>
                    <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">OVR</th>
                    <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">潜力</th>
                    <th className="text-left text-xs text-[#4B4B6A] pb-2 font-medium">所属球队</th>
                    <th className="text-right text-xs text-[#4B4B6A] pb-2 font-medium">系统估值</th>
                    <th className="text-right text-xs text-[#4B4B6A] pb-2 font-medium">挂牌价</th>
                    <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">状态</th>
                    <th className="text-right text-xs text-[#4B4B6A] pb-2 font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {players.map((p) => (
                    <tr key={p.player_id} className="border-b border-[#2D2D44]/50 hover:bg-[#1E1E2D]/50 transition-colors">
                      <td className="py-3">
                        <Link to={`/players/${p.player_id}`} className="text-sm font-medium text-white hover:text-[#0D7377] transition-colors">
                          {p.name}
                        </Link>
                      </td>
                      <td className="text-center">
                        <span className={clsx('text-xs px-2 py-0.5 font-bold', POSITION_COLORS[p.position as keyof typeof POSITION_COLORS] || 'bg-[#2D2D44] text-white')}>
                          {p.position}
                        </span>
                      </td>
                      <td className="text-center text-sm text-[#E2E2F0]">{p.age}</td>
                      <td className="text-center text-sm font-bold stat-number">{p.ovr}</td>
                      <td className="text-center">
                        <span className={clsx(
                          'text-xs font-bold',
                          p.potential_letter === 'S' ? 'text-yellow-400' :
                          p.potential_letter === 'A' ? 'text-[#0D7377]' :
                          'text-[#8B8BA7]'
                        )}>
                          {p.potential_letter}
                        </span>
                      </td>
                      <td className="text-sm text-[#8B8BA7]">{p.team_name}</td>
                      <td className="text-right text-sm text-[#8B8BA7]">{(p.market_value / 10000).toFixed(1)}万</td>
                      <td className="text-right text-sm font-bold text-[#0D7377]">
                        {p.list_price ? `${(p.list_price / 10000).toFixed(1)}万` : '-'}
                      </td>
                      <td className="text-center">
                        {p.is_listed ? (
                          <span className="text-xs px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">挂牌中</span>
                        ) : (
                          <span className="text-xs px-2 py-0.5 bg-[#2D2D44] text-[#4B4B6A]">-</span>
                        )}
                      </td>
                      <td className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            to={`/players/${p.player_id}`}
                            className="p-1.5 bg-[#12121A] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 text-[#8B8BA7] hover:text-white transition-colors"
                          >
                            <Eye className="w-3 h-3" />
                          </Link>
                          <button
                            onClick={() => openOfferModal(p)}
                            className="px-3 py-1.5 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-xs font-bold border-2 border-[#0A5A5D] transition-colors flex items-center gap-1"
                          >
                            <Send className="w-3 h-3" />
                            报价
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {players.length === 0 && (
              <div className="text-center py-12 text-[#8B8BA7]">
                <p className="text-sm">暂无符合条件的球员</p>
              </div>
            )}
          </div>

          {/* Pagination */}
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

      {/* Offer Modal */}
      {offerPlayer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md bg-[#12121A] border-2 border-[#2D2D44] shadow-pixel-lg">
            <div className="flex items-center justify-between p-4 border-b-2 border-[#2D2D44]">
              <h3 className="text-lg font-bold text-white">
                {offerSuccess ? '报价已发送' : `报价: ${offerPlayer.name}`}
              </h3>
              <button onClick={closeOfferModal} className="text-[#8B8BA7] hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 space-y-4">
              {offerSuccess ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <Banknote className="w-5 h-5" />
                    <span className="font-bold">报价发送成功！</span>
                  </div>
                  <p className="text-sm text-[#8B8BA7]">
                    报价金额: <span className="text-white font-bold">{offerAmount}万</span>
                  </p>
                  <button
                    onClick={closeOfferModal}
                    className="w-full py-2 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-sm font-bold border-2 border-[#0A5A5D] transition-colors"
                  >
                    确定
                  </button>
                </div>
              ) : (
                <>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">球员</span>
                      <span className="text-white font-medium">{offerPlayer.name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">所属球队</span>
                      <span className="text-white">{offerPlayer.team_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">系统估值</span>
                      <span className="text-[#0D7377] font-bold">{(offerPlayer.market_value / 10000).toFixed(1)}万</span>
                    </div>
                    {offerPlayer.list_price && (
                      <div className="flex justify-between">
                        <span className="text-[#8B8BA7]">挂牌价</span>
                        <span className="text-emerald-400 font-bold">{(offerPlayer.list_price / 10000).toFixed(1)}万</span>
                      </div>
                    )}
                  </div>

                  <div className="pt-2">
                    <label className="text-xs text-[#8B8BA7] mb-1 block">报价金额（万）</label>
                    <input
                      type="number"
                      value={offerAmount}
                      onChange={e => setOfferAmount(e.target.value)}
                      className="w-full bg-[#1A1A2E] border-2 border-[#2D2D44] px-3 py-2 text-sm text-white focus:border-[#0D7377] outline-none"
                      placeholder="输入报价金额"
                    />
                  </div>

                  {offerError && (
                    <div className="flex items-center gap-2 p-3 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-sm">
                      <AlertTriangle className="w-4 h-4" />
                      {offerError}
                    </div>
                  )}

                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={closeOfferModal}
                      className="flex-1 py-2 bg-[#2D2D44] hover:bg-[#3D3D5C] text-white text-sm font-bold border-2 border-[#2D2D44] transition-colors"
                    >
                      取消
                    </button>
                    <button
                      onClick={submitOffer}
                      disabled={offerLoading || !offerAmount || Number(offerAmount) <= 0}
                      className="flex-1 py-2 bg-[#0D7377] hover:bg-[#0A5A5D] disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-bold border-2 border-[#0A5A5D] transition-colors"
                    >
                      {offerLoading ? '发送中...' : '确认报价'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
