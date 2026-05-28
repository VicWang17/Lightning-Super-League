import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  Users,
  Tree,
  ToolCase,
  Transfer,
  Loader,
  WarningDiamond
} from '../../components/ui/pixel-icons'
import { api } from '../../api/client'

interface TransactionItem {
  id: string
  source_type: string
  amount: number
  description: string
  created_at: string
}

const sourceConfig: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  wage: { label: '球员工资', icon: Users, color: 'text-red-400' },
  youth: { label: '青训投入', icon: Tree, color: 'text-emerald-400' },
  transfer: { label: '转会支出', icon: Transfer, color: 'text-yellow-400' },
  penalty: { label: '罚金', icon: WarningDiamond, color: 'text-orange-400' },
  facility: { label: '设施维护', icon: ToolCase, color: 'text-blue-400' },
  manual_adjustment: { label: '系统调整', icon: ToolCase, color: 'text-gray-400' },
}

function formatWan(value: number): string {
  return (value / 10000).toFixed(1)
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

export default function ExpenseDetails() {
  const [items, setItems] = useState<TransactionItem[]>([])
  const [total, setTotal] = useState(0)
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
        const res = await api.getFinanceTransactions(teamId, { direction: 'expense', page_size: 100 })
        if (!cancelled && res.success && res.data) {
          setItems(res.data.items)
          setTotal(res.data.items.reduce((s, i) => s + i.amount, 0))
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

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-400">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">财务中心</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">支出明细</p>
        </div>
      </div>

      {/* 子导航 */}
      <div className="flex gap-2 border-b-2 border-[#2D2D44]">
        {[
          { id: 'overview', label: '财务总览', to: '/finance/overview' },
          { id: 'budget', label: '预算规划', to: '/finance/budget' },
          { id: 'income', label: '收入明细', to: '/finance/income' },
          { id: 'expense', label: '支出明细', to: '/finance/expense' },
        ].map((tab) => (
          <Link
            key={tab.id}
            to={tab.to}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-0.5',
              tab.id === 'expense'
                ? 'border-[#0D7377] text-[#0D7377]'
                : 'border-transparent text-[#4B4B6A] hover:text-[#8B8BA7]'
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">支出记录</h3>
          <span className="text-sm font-bold text-red-400">合计: {formatWan(total)}万</span>
        </div>
        
        <div className="space-y-2">
          {items.length === 0 && (
            <p className="text-sm text-[#4B4B6A]">暂无支出记录</p>
          )}
          {items.map((item) => {
            const config = sourceConfig[item.source_type] || { label: item.source_type, icon: ToolCase, color: 'text-gray-400' }
            const Icon = config.icon
            return (
              <div key={item.id} className="flex items-center gap-4 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                <div className="w-10 h-10 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center">
                  <Icon className={clsx('w-5 h-5', config.color)} />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{item.description || config.label}</p>
                  <p className="text-xs text-[#4B4B6A]">{formatDate(item.created_at)}</p>
                </div>
                <span className="text-sm font-bold text-red-400">-{formatWan(item.amount)}万</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
