import { SegmentedTabs } from '../ui/SegmentedTabs'

const TABS = [
  { path: '/youth/academy', label: '青训营' },
  { path: '/youth/young-players', label: '年轻球员' },
]

export function YouthTabs() {
  return <SegmentedTabs tabs={TABS} mode="route" />
}
