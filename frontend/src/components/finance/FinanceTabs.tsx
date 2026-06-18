import { SegmentedTabs } from '../ui/SegmentedTabs'

const TABS = [
  { path: '/finance/overview', label: '财务总览' },
  { path: '/finance/budget', label: '预算规划' },
  { path: '/finance/income', label: '收入明细' },
  { path: '/finance/expense', label: '支出明细' },
]

export function FinanceTabs() {
  return <SegmentedTabs tabs={TABS} mode="route" />
}
