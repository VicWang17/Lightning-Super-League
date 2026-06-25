import { SegmentedTabs } from '../ui/SegmentedTabs'

const TABS = [
  { path: '/youth/academy', label: '青训营' },
  { path: '/youth/growth', label: '成长曲线' },
  { path: '/youth/rookie-market', label: '新人市场' },
]

export function YouthTabs() {
  return <SegmentedTabs tabs={TABS} mode="route" />
}
