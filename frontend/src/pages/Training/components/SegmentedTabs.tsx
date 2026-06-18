import { SegmentedTabs as BaseSegmentedTabs } from '../../../components/ui/SegmentedTabs'

const TABS = [
  { path: '/training/weekly', label: '周计划' },
  { path: '/training/calendar', label: '日程' },
  { path: '/training/fatigue', label: '疲劳' },
  { path: '/training/progress', label: '成长曲线' },
]

export function SegmentedTabs() {
  return <BaseSegmentedTabs tabs={TABS} mode="route" />
}
