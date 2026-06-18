import {
  Calendar,
  Clock,
  Target,
  TrendingUp,
  Zap,
} from '../../../components/ui/pixel-icons'
import { SegmentedTabs as BaseSegmentedTabs } from '../../../components/ui/SegmentedTabs'

const TABS = [
  { path: '/training/weekly', label: '周计划', icon: Target },
  { path: '/training/calendar', label: '日程', icon: Calendar },
  { path: '/training/fatigue', label: '疲劳', icon: Zap },
  { path: '/training/history', label: '历史', icon: Clock },
  { path: '/training/progress', label: '成长曲线', icon: TrendingUp },
]

export function SegmentedTabs() {
  return <BaseSegmentedTabs tabs={TABS} mode="route" />
}
