import { useState, useEffect } from 'react'
import { Loader } from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import { PageHeader } from '../../components/ui/PageHeader'
import { FinanceTabs } from '../../components/finance/FinanceTabs'

interface TransactionItem {
  id: string
  source_type: string
  amount: number
  description: string
  created_at: string
}

const sourceConfig: Record<string, { label: string }> = {
  wage: { label: '球员工资' },
  youth: { label: '青训投入' },
  transfer: { label: '转会支出' },
  penalty: { label: '罚金' },
  facility: { label: '设施维护' },
  manual_adjustment: { label: '系统调整' },
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
        <Loader className="w-8 h-8 text-[#1F5F43] animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-[#FF6F59]">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <PageHeader title="支出明细" subtitle="球队各项支出去向明细" />

      <FinanceTabs />

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">支出记录</h3>
          <span className="text-sm font-bold text-[#FF6F59]">合计: {formatWan(total)}万</span>
        </div>
        
        <div className="space-y-2">
          {items.length === 0 && (
            <p className="text-sm text-[#8B5A2B]/40">暂无支出记录</p>
          )}
          {items.map((item) => {
            const config = sourceConfig[item.source_type] || { label: item.source_type }
            return (
              <div key={item.id} className="flex items-center gap-4 p-3 bg-white/70 border-2 border-[#1F5F43]/20">
                <div className="flex-1">
                  <p className="text-sm font-medium text-[#173126]">{item.description || config.label}</p>
                  <p className="text-xs text-[#8B5A2B]/40">{formatDate(item.created_at)}</p>
                </div>
                <span className="text-sm font-bold text-[#FF6F59]">-{formatWan(item.amount)}万</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}


