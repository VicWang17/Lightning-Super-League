import { useState } from 'react'
import { PageHeader } from '../../components/ui/PageHeader'
import ListedPlayersTab from './Market'
import FreeAgentsTab from './FreeMarket'
import RecentMarketTab from './History'

const TABS = [
  { id: 'listed', label: '挂牌球员' },
  { id: 'free', label: '自由球员市场' },
  { id: 'recent', label: '近期市场' },
] as const

type MarketTab = (typeof TABS)[number]['id']

export default function MarketPage() {
  const [activeTab, setActiveTab] = useState<MarketTab>('listed')

  return (
    <div className="fresh-page-shell space-y-6">
      <PageHeader title="转会市场" subtitle="挂牌、自由签约与近期动态" />

      <div className="flex flex-wrap gap-2">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={[
              'px-4 py-2 text-sm font-bold border-2 transition-colors',
              activeTab === tab.id
                ? 'bg-[#1F5F43] text-[#F8FFD2] border-[#1F5F43]'
                : 'bg-[#FFF8DC]/80 text-[#466353] border-[#1F5F43]/20 hover:border-[#1F5F43] hover:text-[#173126]',
            ].join(' ')}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'listed' && <ListedPlayersTab embedded forceListed />}
      {activeTab === 'free' && <FreeAgentsTab embedded />}
      {activeTab === 'recent' && <RecentMarketTab embedded />}
    </div>
  )
}
