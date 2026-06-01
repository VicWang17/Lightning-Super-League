import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, Funnel, X, Check } from 'lucide-react'
import { 
  Clock,
  WarningDiamond,
  ChevronLeft,
  ChevronRight,
  Loader
} from '../../components/ui/pixel-icons'
import api from '../../api/client'
import type { FreeMarketPlayer, FreeMarketPreview, FreeMarketSignResult } from '../../types/free_market'
import { ORIGIN_NAMES, ORIGIN_COLORS } from '../../types/free_market'

const positionOptions = [
  { value: '', label: '全部位置' },
  { value: 'FW', label: '前锋' },
  { value: 'MF', label: '中场' },
  { value: 'DF', label: '后卫' },
  { value: 'GK', label: '门将' },
]

const originOptions = [
  { value: '', label: '全部来源' },
  { value: 'CONTRACT_EXPIRED', label: '合同到期' },
  { value: 'RELEASED', label: '解约球员' },
  { value: 'ACADEMY_RELEASED', label: '青训新人' },
  { value: 'AUTO_GENERATED', label: '系统兜底' },
]

const positionColors: Record<string, string> = {
  FW: 'bg-red-500 text-white',
  MF: 'bg-emerald-500 text-white',
  DF: 'bg-blue-500 text-white',
  GK: 'bg-amber-500 text-black',
}

interface Filters {
  position: string
  min_ovr: string
  max_ovr: string
  min_age: string
  max_age: string
  origin: string
}

export default function FreeMarket() {
  const [players, setPlayers] = useState<FreeMarketPlayer[]>([])
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
    origin: '',
  })
  const [showFilters, setShowFilters] = useState(false)

  // Modal states
  const [selectedPlayer, setSelectedPlayer] = useState<FreeMarketPlayer | null>(null)
  const [preview, setPreview] = useState<FreeMarketPreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [signing, setSigning] = useState(false)
  const [signSuccess, setSignSuccess] = useState<FreeMarketSignResult | null>(null)

  const fetchPlayers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string | number> = { page, page_size: 12 }
      if (filters.position) params.position = filters.position
      if (filters.min_ovr) params.min_ovr = Number(filters.min_ovr)
      if (filters.max_ovr) params.max_ovr = Number(filters.max_ovr)
      if (filters.min_age) params.min_age = Number(filters.min_age)
      if (filters.max_age) params.max_age = Number(filters.max_age)
      if (filters.origin) params.origin = filters.origin

      const res = await api.getFreeMarketList(params)
      if (res.success && res.data) {
        setPlayers(res.data.items)
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

  const resetFilters = () => {
    setFilters({ position: '', min_ovr: '', max_ovr: '', min_age: '', max_age: '', origin: '' })
    setPage(1)
  }

  const openSignModal = async (player: FreeMarketPlayer) => {
    setSelectedPlayer(player)
    setPreview(null)
    setPreviewError(null)
    setSignSuccess(null)
    setPreviewLoading(true)

    try {
      const teamRes = await api.get<{ id: string }>('/teams/my-team')
      if (!teamRes.success || !teamRes.data) {
        setPreviewError('无法获取球队信息')
        setPreviewLoading(false)
        return
      }
      const teamId = teamRes.data.id

      const res = await api.previewFreeMarketSign(player.listing_id, {
        team_id: teamId,
        years: 2,
        wage: player.recommended_wage,
        squad_role: 'rotation',
      })
      if (res.success && res.data) {
        setPreview(res.data)
      } else {
        setPreviewError(res.message || '预览失败')
      }
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : '预览请求失败')
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleSign = async () => {
    if (!selectedPlayer || !preview) return
    setSigning(true)
    setPreviewError(null)
    try {
      const teamRes = await api.get<{ id: string }>('/teams/my-team')
      if (!teamRes.success || !teamRes.data) {
        setPreviewError('无法获取球队信息')
        setSigning(false)
        return
      }
      const teamId = teamRes.data.id

      const res = await api.signFreeMarketPlayer(selectedPlayer.listing_id, {
        team_id: teamId,
        years: 2,
        wage: selectedPlayer.recommended_wage,
        squad_role: 'rotation',
      })
      if (res.success && res.data) {
        setSignSuccess(res.data)
        // 刷新列表
        fetchPlayers()
      } else {
        setPreviewError(res.message || '签约失败')
      }
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : '签约请求失败')
    } finally {
      setSigning(false)
    }
  }

  const closeModal = () => {
    setSelectedPlayer(null)
    setPreview(null)
    setPreviewError(null)
    setSignSuccess(null)
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">转会市场</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">一口价签约，无需竞价</p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2 px-3 py-2 bg-[#12121A] border-2 border-[#2D2D44] text-sm text-[#8B8BA7] hover:text-white hover:border-[#0D7377]/50 transition-colors"
        >
          <Funnel className="w-4 h-4" />
          筛选
        </button>
      </div>

      {/* 子导航 */}
      <div className="flex gap-2 border-b-2 border-[#2D2D44]">
        {[
          { id: 'auction', label: '拍卖市场', to: '/transfer/market' },
          { id: 'free', label: '自由市场', to: '/transfer/free-market' },
          { id: 'watchlist', label: '我的关注', to: '/transfer/watchlist' },
          { id: 'my-listings', label: '我的挂牌', to: '/transfer/my-listings' },
          { id: 'history', label: '转会历史', to: '/transfer/history' },
        ].map((tab) => (
          <Link
            key={tab.id}
            to={tab.to}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-0.5',
              tab.id === 'free'
                ? 'border-[#0D7377] text-[#0D7377]'
                : 'border-transparent text-[#4B4B6A] hover:text-[#8B8BA7]'
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      {/* 提示 */}
      <div className="flex items-center gap-3 p-3 bg-yellow-500/10 border-2 border-yellow-500/30">
        <WarningDiamond className="w-4 h-4 text-yellow-400 flex-shrink-0" />
        <p className="text-sm text-yellow-400">
          每48小时内最多从自由市场签约2名球员。价格每24小时自动下调5%。
        </p>
      </div>

      {/* 筛选面板 */}
      {showFilters && (
        <div className="p-4 bg-[#12121A] border-2 border-[#2D2D44] space-y-3">
          <div className="flex flex-wrap gap-3">
            <select
              value={filters.position}
              onChange={e => handleFilterChange('position', e.target.value)}
              className="px-3 py-2 bg-[#1A1A2E] border-2 border-[#2D2D44] text-sm text-white focus:border-[#0D7377] outline-none"
            >
              {positionOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <select
              value={filters.origin}
              onChange={e => handleFilterChange('origin', e.target.value)}
              className="px-3 py-2 bg-[#1A1A2E] border-2 border-[#2D2D44] text-sm text-white focus:border-[#0D7377] outline-none"
            >
              {originOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <input
              type="number"
              placeholder="最低OVR"
              value={filters.min_ovr}
              onChange={e => handleFilterChange('min_ovr', e.target.value)}
              className="w-24 px-3 py-2 bg-[#1A1A2E] border-2 border-[#2D2D44] text-sm text-white placeholder:text-[#4B4B6A] focus:border-[#0D7377] outline-none"
            />
            <input
              type="number"
              placeholder="最高OVR"
              value={filters.max_ovr}
              onChange={e => handleFilterChange('max_ovr', e.target.value)}
              className="w-24 px-3 py-2 bg-[#1A1A2E] border-2 border-[#2D2D44] text-sm text-white placeholder:text-[#4B4B6A] focus:border-[#0D7377] outline-none"
            />
            <input
              type="number"
              placeholder="最低年龄"
              value={filters.min_age}
              onChange={e => handleFilterChange('min_age', e.target.value)}
              className="w-24 px-3 py-2 bg-[#1A1A2E] border-2 border-[#2D2D44] text-sm text-white placeholder:text-[#4B4B6A] focus:border-[#0D7377] outline-none"
            />
            <input
              type="number"
              placeholder="最高年龄"
              value={filters.max_age}
              onChange={e => handleFilterChange('max_age', e.target.value)}
              className="w-24 px-3 py-2 bg-[#1A1A2E] border-2 border-[#2D2D44] text-sm text-white placeholder:text-[#4B4B6A] focus:border-[#0D7377] outline-none"
            />
            <button
              onClick={resetFilters}
              className="px-3 py-2 text-sm text-[#8B8BA7] hover:text-white border-2 border-[#2D2D44] hover:border-[#8B8BA7] transition-colors"
            >
              重置
            </button>
          </div>
        </div>
      )}

      {/* 加载 & 错误 */}
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

      {/* 球员列表 */}
      {!loading && !error && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {players.map((p) => (
              <div key={p.listing_id} className="card card-hover">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h4 className="font-bold text-white">{p.name}</h4>
                    <p className="text-xs text-[#8B8BA7]">{p.age}岁 · OVR {p.ovr} · 潜力 {p.potential_letter}</p>
                  </div>
                  <span className={clsx('text-xs px-2 py-0.5 font-bold', positionColors[p.position] || 'bg-[#2D2D44] text-white')}>
                    {p.position}
                  </span>
                </div>
                
                <div className="flex items-center gap-2 mb-3">
                  <span className={clsx('text-xs', ORIGIN_COLORS[p.origin as keyof typeof ORIGIN_COLORS] || 'text-[#8B8BA7]')}>
                    {ORIGIN_NAMES[p.origin as keyof typeof ORIGIN_NAMES] || p.origin}
                  </span>
                  {p.is_rookie_protected && (
                    <span className="text-xs px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      新人保护期
                    </span>
                  )}
                </div>

                <div className="space-y-2 mb-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[#4B4B6A]">签字费</span>
                    <span className="text-lg font-bold text-[#0D7377] stat-number">{p.signing_fee}万</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[#4B4B6A]">建议周薪</span>
                    <span className="text-xs text-white">{p.recommended_wage}万/周</span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t-2 border-[#2D2D44]">
                  <span className="text-xs text-[#4B4B6A] flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    第{p.listed_at_day}天上架
                  </span>
                  <button
                    onClick={() => openSignModal(p)}
                    className="px-4 py-1.5 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-xs font-bold border-2 border-[#0A5A5D] transition-colors"
                  >
                    签约
                  </button>
                </div>
              </div>
            ))}
          </div>

          {players.length === 0 && (
            <div className="text-center py-12 text-[#8B8BA7]">
              <p className="text-sm">暂无符合条件的自由球员</p>
            </div>
          )}

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 bg-[#12121A] border-2 border-[#2D2D44] text-[#8B8BA7] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-[#8B8BA7]">
                第 {page} / {totalPages} 页
              </span>
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

      {/* 签约弹窗 */}
      {selectedPlayer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md bg-[#12121A] border-2 border-[#2D2D44] shadow-pixel-lg">
            <div className="flex items-center justify-between p-4 border-b-2 border-[#2D2D44]">
              <h3 className="text-lg font-bold text-white">
                {signSuccess ? '签约成功' : `签约 ${selectedPlayer.name}`}
              </h3>
              <button onClick={closeModal} className="text-[#8B8BA7] hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 space-y-4">
              {previewLoading && (
                <div className="flex items-center justify-center py-8">
                  <Loader className="w-6 h-6 text-[#0D7377] animate-spin" />
                </div>
              )}

              {previewError && (
                <div className="flex items-center gap-2 p-3 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-sm">
                  <AlertTriangle className="w-4 h-4" />
                  {previewError}
                </div>
              )}

              {signSuccess && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <Check className="w-5 h-5" />
                    <span className="font-bold">签约完成！</span>
                  </div>
                  <div className="space-y-2 text-sm text-[#8B8BA7]">
                    <p>合同ID: <span className="text-white font-mono">{signSuccess.contract_id}</span></p>
                    <p>球员ID: <span className="text-white font-mono">{signSuccess.player_id}</span></p>
                    <p>签字费: <span className="text-[#0D7377] font-bold">{signSuccess.signing_fee}万</span></p>
                  </div>
                  <button
                    onClick={closeModal}
                    className="w-full py-2 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-sm font-bold border-2 border-[#0A5A5D] transition-colors"
                  >
                    确定
                  </button>
                </div>
              )}

              {preview && !signSuccess && (
                <div className="space-y-3">
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">签字费</span>
                      <span className="text-[#0D7377] font-bold">{preview.signing_fee}万</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">周薪</span>
                      <span className="text-white">{preview.offered_wage}万</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">建议周薪</span>
                      <span className="text-white">{preview.recommended_wage}万</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">薪资满意度</span>
                      <span className={preview.wage_ratio >= 1 ? 'text-emerald-400' : preview.wage_ratio >= 0.8 ? 'text-yellow-400' : 'text-red-400'}>
                        {Math.round(preview.wage_ratio * 100)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">球员反应</span>
                      <span className="text-white">{preview.visible_reaction}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">签约后薪资帽占比</span>
                      <span className="text-white">{Math.round(preview.wage_cap_after_pct * 100)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">余额（扣签字费后）</span>
                      <span className={preview.can_pay_signing_fee ? 'text-emerald-400' : 'text-red-400'}>
                        {preview.balance_after_fee}万
                      </span>
                    </div>
                  </div>

                  {preview.warnings.length > 0 && (
                    <div className="space-y-1">
                      {preview.warnings.map((w, i) => (
                        <p key={i} className="text-xs text-yellow-400 flex items-start gap-1">
                          <AlertTriangle className="w-3 h-3 flex-shrink-0 mt-0.5" />
                          {w}
                        </p>
                      ))}
                    </div>
                  )}

                  {!preview.can_submit && (
                    <div className="p-2 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-xs">
                      当前条件不满足签约要求
                    </div>
                  )}
                  {!preview.can_pay_signing_fee && (
                    <div className="p-2 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-xs">
                      余额不足以支付签字费
                    </div>
                  )}

                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={closeModal}
                      className="flex-1 py-2 bg-[#2D2D44] hover:bg-[#3D3D5C] text-white text-sm font-bold border-2 border-[#2D2D44] transition-colors"
                    >
                      取消
                    </button>
                    <button
                      onClick={handleSign}
                      disabled={signing || !preview.can_submit || !preview.can_pay_signing_fee}
                      className="flex-1 py-2 bg-[#0D7377] hover:bg-[#0A5A5D] disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-bold border-2 border-[#0A5A5D] transition-colors"
                    >
                      {signing ? '签约中...' : '确认签约'}
                    </button>
                  </div>
                </div>
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
