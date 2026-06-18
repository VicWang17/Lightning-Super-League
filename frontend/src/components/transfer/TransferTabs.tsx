import { SegmentedTabs } from '../ui/SegmentedTabs'

const TABS = [
  { path: '/transfer/market', label: '拍卖市场' },
  { path: '/transfer/free-market', label: '自由市场' },
  { path: '/transfer/watchlist', label: '我的关注' },
  { path: '/transfer/my-listings', label: '我的挂牌' },
  { path: '/transfer/public-offers', label: '公开报价' },
  { path: '/transfer/my-offers', label: '我的报价' },
  { path: '/transfer/history', label: '转会历史' },
]

export function TransferTabs() {
  return <SegmentedTabs tabs={TABS} mode="route" />
}
