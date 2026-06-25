import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { clsx } from 'clsx'
import { ChevronRight, Loader } from '../../components/ui/pixel-icons'
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

const ratingConfig: Record<string, { tone: string; label: string }> = {
  A: { tone: 'lime', label: '优秀' },
  B: { tone: 'sky', label: '健康' },
  C: { tone: 'amber', label: '紧张' },
  D: { tone: 'coral', label: '危险' },
}

const toneClasses: Record<string, string> = {
  lime: 'bg-[#B9EF3F] text-[#1F5F43] border-[#1F5F43]',
  sky: 'bg-[#59C7EE] text-[#173126] border-[#1F5F43]',
  amber: 'bg-[#FFC247] text-[#8B5A2B] border-[#1F5F43]',
  coral: 'bg-[#FF6F59] text-[#F8FFD2] border-[#1F5F43]',
}

function formatWan(value: number) {
  return `${(value / 10000).toFixed(1)}万`
}

function Meter({ label, value, total, tone }: { label: string; value: number; total: number; tone: string }) {
  const pct = total > 0 ? Math.min(100, (value / total) * 100) : 0
  return (
    <div className="fresh-meter">
      <div>
        <span>{label}</span>
        <strong>{formatWan(value)}</strong>
      </div>
      <div className="fresh-meter-track">
        <div className={`fresh-meter-fill tone-${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
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
        <Loader className="w-8 h-8 text-[#1F5F43] animate-spin" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-[#FF6F59] font-black">{error || '数据加载失败'}</p>
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
    { label: '转播收入', value: data.income_breakdown.broadcast, tone: 'sky' as const },
    { label: '商业赞助', value: data.income_breakdown.sponsor, tone: 'amber' as const },
    { label: '比赛奖金', value: data.income_breakdown.match_bonus, tone: 'lime' as const },
    { label: '杯赛奖金', value: data.income_breakdown.cup_prize, tone: 'coral' as const },
    { label: '联赛分红', value: data.income_breakdown.league_prize, tone: 'amber' as const },
  ].filter(i => i.value > 0)

  const expenseItems = [
    { label: '球员工资', value: data.expense_breakdown.wage, tone: 'coral' as const },
    { label: '青训投入', value: data.expense_breakdown.youth, tone: 'lime' as const },
    { label: '转会支出', value: data.expense_breakdown.transfer, tone: 'amber' as const },
    { label: '罚金', value: data.expense_breakdown.penalty, tone: 'coral' as const },
  ].filter(i => i.value > 0)

  const wageTone = cap.wage_pressure_pct > 90 ? 'coral' : cap.wage_pressure_pct > 70 ? 'amber' : 'lime'

  return (
    <div className="fresh-page-shell space-y-6">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-sm font-bold text-[#466353] hover:text-[#173126] transition-colors"
      >
        <ChevronRight className="w-4 h-4 rotate-180" />
        返回上一页
      </button>

      <PageHeader title="财务总览" subtitle="球队财务总览与预算管理" />

      <FinanceTabs />

      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="fresh-stat-tile">
          <span>当前余额</span>
          <strong className={clsx(balance >= 0 ? 'text-[#173126]' : 'text-[#FF6F59]')}>
            {formatWan(balance)}万
          </strong>
        </div>
        <div className="fresh-stat-tile">
          <span>赛季总收入</span>
          <strong>{formatWan(totalIncome)}万</strong>
        </div>
        <div className="fresh-stat-tile">
          <span>赛季总支出</span>
          <strong>{formatWan(totalExpense)}万</strong>
        </div>
        <div className="fresh-stat-tile">
          <span>财务评级</span>
          <div className="flex items-center gap-2 mt-1">
            <strong>{healthRating}</strong>
            <span className={clsx('px-2 py-0.5 text-[10px] font-black border-2', toneClasses[rating.tone])}>
              {rating.label}
            </span>
          </div>
        </div>
      </section>

      <section className="fresh-ticket space-y-4">
        <div className="flex items-center justify-between gap-4">
          <h3 className="text-lg font-black text-[#173126]">工资压力监控</h3>
          <span className={clsx('px-2 py-0.5 text-[10px] font-black border-2', toneClasses[wageTone])}>
            {cap.wage_pressure_pct}%
          </span>
        </div>
        <div className="fresh-meter-track h-4">
          <div className={`fresh-meter-fill tone-${wageTone}`} style={{ width: `${Math.min(cap.wage_pressure_pct, 100)}%` }} />
        </div>
        <div className="flex items-center justify-between text-xs font-bold text-[#466353]">
          <span>当前: {formatWan(cap.wage_bill)}万</span>
          <span>参考线: {formatWan(cap.wage_cap)}万</span>
        </div>
        {cap.wage_pressure_pct > 90 && (
          <div className="p-2 bg-[#FF6F59]/12 border-2 border-[#FF6F59]/30 text-[#FF6F59] text-xs font-black">
            工资压力偏高，会影响财务健康
          </div>
        )}
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="fresh-ticket space-y-4">
          <h3 className="text-lg font-black text-[#173126]">收入构成</h3>
          {incomeItems.map((item) => (
            <Meter key={item.label} label={item.label} value={item.value} total={totalIncome} tone={item.tone} />
          ))}
          {incomeItems.length === 0 && (
            <p className="text-sm font-bold text-[#466353]">暂无收入记录</p>
          )}
          <Link to="/finance/income" className="inline-flex items-center gap-1 text-sm font-black text-[#1F5F43] hover:text-[#173126] transition-colors">
            查看明细 <ChevronRight className="w-3 h-3" />
          </Link>
        </div>

        <div className="fresh-ticket space-y-4">
          <h3 className="text-lg font-black text-[#173126]">支出构成</h3>
          {expenseItems.map((item) => (
            <Meter key={item.label} label={item.label} value={item.value} total={totalExpense} tone={item.tone} />
          ))}
          {expenseItems.length === 0 && (
            <p className="text-sm font-bold text-[#466353]">暂无支出记录</p>
          )}
          <Link to="/finance/expense" className="inline-flex items-center gap-1 text-sm font-black text-[#1F5F43] hover:text-[#173126] transition-colors">
            查看明细 <ChevronRight className="w-3 h-3" />
          </Link>
        </div>
      </section>
    </div>
  )
}
