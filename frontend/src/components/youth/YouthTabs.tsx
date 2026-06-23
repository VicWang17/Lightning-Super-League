import { SegmentedTabs } from '../ui/SegmentedTabs'

const TABS = [
  { path: '/youth/academy', label: '青训营' },
  { path: '/youth/young-players', label: '年轻球员' },
  { path: '/youth/rookie-market', label: '新人市场' },
]

export function YouthTabs() {
  return <SegmentedTabs tabs={TABS} mode="route" />
}
