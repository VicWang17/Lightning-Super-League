import { useParams, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { ChevronLeft, Transfer, Calendar, Money, Building } from '../../components/ui/pixel-icons'
import { Card } from '../../components/ui/Card'
import { PlayerTabs } from '../../components/players/PlayerTabs'
import { api } from '../../api/client'
import type { TransferRecordItem } from '../../types/transfer'

const TRANSFER_TYPE_NAMES: Record<string, string> = {
  CLUB_TRANSFER: '队间转会',
  TRANSFER: '队间转会',
  club_transfer: '队间转会',
  RELEASE: '解约',
  release: '解约',
  FREE_MARKET_SIGNING: '自由签约',
  FREE_AGENT: '自由签约',
  free_market_signing: '自由签约',
}

const TRANSFER_TYPE_COLORS: Record<string, string> = {
  CLUB_TRANSFER: 'text-[#0D7377]',
  TRANSFER: 'text-[#0D7377]',
  club_transfer: 'text-[#0D7377]',
  RELEASE: 'text-red-400',
  release: 'text-red-400',
  FREE_MARKET_SIGNING: 'text-emerald-400',
  FREE_AGENT: 'text-emerald-400',
  free_market_signing: 'text-emerald-400',
}

function PlayerTransfers() {
  const { id } = useParams<{ id: string }>()
  const [records, setRecords] = useState<TransferRecordItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    api.getTransferHistory({ player_id: id, page_size: 100 })
      .then(res => {
        if (res.success && res.data) {
          setRecords(res.data.items || [])
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return <div className="max-w-[1200px] p-8 text-center text-[#8B8BA7]">加载中...</div>
  }

  return (
    <div className="max-w-[1200px]">
      <Link
        to={`/players/${id}`}
        className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors mb-4"
      >
        <ChevronLeft className="w-4 h-4" />
        返回球员档案
      </Link>

      <PlayerTabs playerId={id!} />

      <Card>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Transfer className="w-5 h-5 text-[#C6F135]" />
          转会记录
        </h3>

        {records.length === 0 ? (
          <p className="text-[#8B8BA7] text-center py-8">暂无转会记录</p>
        ) : (
          <div className="space-y-3">
            {records.map((record) => (
              <div
                key={record.record_id}
                className="flex flex-col md:flex-row md:items-center gap-4 p-4 bg-[#1E1E2D] border border-[#2D2D44]"
              >
                <div className="flex items-center gap-3 md:w-48">
                  <div className={`w-2 h-2 ${TRANSFER_TYPE_COLORS[record.transfer_type] || 'text-white'}`}>
                    <Transfer className="w-5 h-5" />
                  </div>
                  <span className={`text-sm font-medium ${TRANSFER_TYPE_COLORS[record.transfer_type] || 'text-white'}`}>
                    {TRANSFER_TYPE_NAMES[record.transfer_type] || record.transfer_type}
                  </span>
                </div>

                <div className="flex-1 flex flex-col md:flex-row md:items-center gap-2 md:gap-6">
                  <div className="flex items-center gap-2 text-sm">
                    <Building className="w-4 h-4 text-[#8B8BA7]" />
                    <span className="text-[#8B8BA7]">来自</span>
                    <Link
                      to={record.from_team_id ? `/teams/${record.from_team_id}` : '#'}
                      className={record.from_team_id ? 'text-[#0D7377] hover:text-[#C6F135] transition-colors' : 'text-[#8B8BA7]'}
                    >
                      {record.from_team_id ? '球队' : '无'}
                    </Link>
                  </div>

                  <div className="flex items-center gap-2 text-sm">
                    <Transfer className="w-4 h-4 text-[#8B8BA7]" />
                    <span className="text-[#8B8BA7]">→</span>
                  </div>

                  <div className="flex items-center gap-2 text-sm">
                    <Building className="w-4 h-4 text-[#8B8BA7]" />
                    <span className="text-[#8B8BA7]">前往</span>
                    <Link
                      to={record.to_team_id ? `/teams/${record.to_team_id}` : '#'}
                      className={record.to_team_id ? 'text-[#0D7377] hover:text-[#C6F135] transition-colors' : 'text-[#8B8BA7]'}
                    >
                      {record.to_team_id ? '球队' : '无'}
                    </Link>
                  </div>
                </div>

                <div className="flex items-center gap-4 md:justify-end">
                  <div className="flex items-center gap-1.5 text-sm">
                    <Money className="w-4 h-4 text-[#C6F135]" />
                    <span className="font-bold stat-number pixel-number text-white">
                      €{(record.amount / 1000000).toFixed(1)}M
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-[#8B8BA7]">
                    <Calendar className="w-3.5 h-3.5" />
                    {new Date(record.completed_at).toLocaleDateString('zh-CN')}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}

export default PlayerTransfers
