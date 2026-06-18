import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  WarningDiamond,
  Check,
  ChevronRight,
  Loader,
  ChevronLeft
} from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import { PageHeader } from '../../components/ui/PageHeader'
import { FinanceTabs } from '../../components/finance/FinanceTabs'

interface FinanceData {
  current_balance: number
  total_income: number
  total_expense: number
  financial_health: string
  wage_cap_info: {
    wage_cap: number
    wage_bill: number
    wage_pressure_pct: number
    status: string
  }
  income_breakdown: {
    broadcast: number
    sponsor: number
    match_bonus: number
    cup_prize: number
    league_prize: number
    other: number
  }
  expense_breakdown: {
    wage: number
    youth: number
    transfer: number
    penalty: number
    other: number
  }
}

const ratingConfig: Record<string, { color: string; bg: string; border: string; label: string }> = {
  A: { color: 'text-emerald-400', bg: 'bg-emerald-500/20', border: 'border-emerald-500/30', label: '优秀' },
  B: { color: 'text-[#0D7377]', bg: 'bg-[#0D4A4D]/30', border: 'border-[#0D7377]/30', label: '健康' },
  C: { color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30', label: '紧张' },
  D: { color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/30', label: '危险' },
}

function formatWan(value: number): string {
  return (value / 10000).toFixed(1)
}

export default function FinanceOverview() {
  const navigate = useNavigate()
  const [data, setData] = useState<FinanceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        setLoading(true)
        const teamRes = await api.get<{ id: string }>('/teams/my-team')
        if (!teamRes.success || !teamRes.data?.id) {
          setError('未找到球队信息')
          return
        }
        const teamId = teamRes.data.id
        const financeRes = await api.getFinanceOverview(teamId)
        if (!cancelled && financeRes.success && financeRes.data) {
          setData(financeRes.data)
        }
      } catch (e: any) {
        if (!cancelled) setError(e.message || '加载失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader className="w-8 h-8 text-[#0D7377] animate-spin" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-400">{error || '数据加载失败'}</p>
      </div>
    )
  }

  const balance = data.current_balance
  const totalIncome = data.total_income
  const totalExpense = data.total_expense
  const healthRating = data.financial_health || 'B'
  const rating = ratingConfig[healthRating] || ratingConfig.B
  const cap = data.wage_cap_info

  const incomeItems = [
    { label: '转播收入', value: data.income_breakdown.broadcast, color: 'bg-blue-500' },
    { label: '商业赞助', value: data.income_breakdown.sponsor, color: 'bg-purple-500' },
    { label: '比赛奖金', value: data.income_breakdown.match_bonus, color: 'bg-emerald-500' },
    { label: '杯赛奖金', value: data.income_breakdown.cup_prize, color: 'bg-yellow-500' },
    { label: '联赛分红', value: data.income_breakdown.league_prize, color: 'bg-[#0D7377]' },
  ].filter(i => i.value > 0)

  const expenseItems = [
    { label: '球员工资', value: data.expense_breakdown.wage, color: 'bg-red-500' },
    { label: '青训投入', value: data.expense_breakdown.youth, color: 'bg-emerald-500' },
    { label: '转会支出', value: data.expense_breakdown.transfer, color: 'bg-yellow-500' },
    { label: '罚金', value: data.expense_breakdown.penalty, color: 'bg-orange-500' },
  ].filter(i => i.value > 0)

  return (
    <div className="space-y-6 max-w-[1400px]">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors mb-4"
      >
        <ChevronLeft className="w-4 h-4" />
        返回上一页
      </button>
      <PageHeader icon={Wallet} title="财务总览" subtitle="球队财务总览与预算管理" />

      <FinanceTabs />

      {/* 核心指标 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Wallet className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">当前余额</span>
          </div>
          <p className={clsx('text-2xl font-bold stat-number', balance >= 0 ? 'text-emerald-400' : 'text-red-400')}>
            {balance >= 0 ? '' : ''}{formatWan(balance)}万
          </p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-[#8B8BA7]">赛季总收入</span>
          </div>
          <p className="text-2xl font-bold text-white stat-number">{formatWan(totalIncome)}万</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown className="w-4 h-4 text-red-400" />
            <span className="text-sm text-[#8B8BA7]">赛季总支出</span>
          </div>
          <p className="text-2xl font-bold text-white stat-number">{formatWan(totalExpense)}万</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Check className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">财务评级</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={clsx('text-2xl font-bold', rating.color)}>{healthRating}</span>
            <span className={clsx('text-xs px-2 py-0.5 border', rating.color, rating.border, rating.bg)}>
              {rating.label}
            </span>
          </div>
        </div>
      </div>

      {/* 工资帽 */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">工资压力监控</h3>
          <span className={clsx(
            'text-xs px-2 py-0.5 border',
            cap.wage_pressure_pct > 90 ? 'text-red-400 border-red-400/30 bg-red-500/10' :
            cap.wage_pressure_pct > 70 ? 'text-yellow-400 border-yellow-400/30 bg-yellow-500/10' :
            'text-emerald-400 border-emerald-400/30 bg-emerald-500/10'
          )}>
            {cap.wage_pressure_pct}%
          </span>
        </div>
        <div className="pixel-progress-track h-4">
          <div 
            className={clsx(
              'pixel-progress-fill h-full',
              cap.wage_pressure_pct > 90 ? 'bg-red-500' :
              cap.wage_pressure_pct > 70 ? 'bg-yellow-500' :
              'bg-emerald-500'
            )}
            style={{ width: `${Math.min(cap.wage_pressure_pct, 100)}%` }}
          />
        </div>
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-[#4B4B6A]">当前: {formatWan(cap.wage_bill)}万</span>
          <span className="text-xs text-[#4B4B6A]">参考线: {formatWan(cap.wage_cap)}万</span>
        </div>
        {cap.wage_pressure_pct > 90 && (
          <div className="flex items-center gap-2 mt-3 p-2 bg-red-500/10 border border-red-500/20">
            <WarningDiamond className="w-4 h-4 text-red-400" />
            <span className="text-xs text-red-400">工资压力偏高，会影响财务健康</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 收入构成 */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">收入构成</h3>
          <div className="space-y-3">
            {incomeItems.map((item) => (
              <div key={item.label}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-[#E2E2F0]">{item.label}</span>
                  <span className="text-sm text-white">{formatWan(item.value)}万</span>
                </div>
                <div className="pixel-progress-track h-2">
                  <div className={clsx('pixel-progress-fill h-full', item.color)} style={{ width: `${totalIncome > 0 ? (item.value / totalIncome) * 100 : 0}%` }} />
                </div>
              </div>
            ))}
            {incomeItems.length === 0 && (
              <p className="text-sm text-[#4B4B6A]">暂无收入记录</p>
            )}
          </div>
          <Link to="/finance/income" className="flex items-center gap-1 text-sm text-[#0D7377] hover:text-white transition-colors mt-4">
            查看明细 <ChevronRight className="w-3 h-3" />
          </Link>
        </div>

        {/* 支出构成 */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">支出构成</h3>
          <div className="space-y-3">
            {expenseItems.map((item) => (
              <div key={item.label}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-[#E2E2F0]">{item.label}</span>
                  <span className="text-sm text-white">{formatWan(item.value)}万</span>
                </div>
                <div className="pixel-progress-track h-2">
                  <div className={clsx('pixel-progress-fill h-full', item.color)} style={{ width: `${totalExpense > 0 ? (item.value / totalExpense) * 100 : 0}%` }} />
                </div>
              </div>
            ))}
            {expenseItems.length === 0 && (
              <p className="text-sm text-[#4B4B6A]">暂无支出记录</p>
            )}
          </div>
          <Link to="/finance/expense" className="flex items-center gap-1 text-sm text-[#0D7377] hover:text-white transition-colors mt-4">
            查看明细 <ChevronRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
