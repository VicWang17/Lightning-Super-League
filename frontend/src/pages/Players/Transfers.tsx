import { useParams, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
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
  renewal: '续约',
  RENEWAL: '续约',
}

const TRANSFER_TYPE_COLORS: Record<string, string> = {
  CLUB_TRANSFER: 'text-[#1F5F43]',
  TRANSFER: 'text-[#1F5F43]',
  club_transfer: 'text-[#1F5F43]',
  RELEASE: 'text-[#FF6F59]',
  release: 'text-[#FF6F59]',
  FREE_MARKET_SIGNING: 'text-[#1F5F43]',
  FREE_AGENT: 'text-[#1F5F43]',
  free_market_signing: 'text-[#1F5F43]',
  renewal: 'text-[#59C7EE]',
  RENEWAL: 'text-[#59C7EE]',
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
    return <div className="max-w-[1200px] p-8 text-center text-[#466353]">加载中...</div>
  }

  return (
    <div className="max-w-[1200px]">
      <Link
        to={`/players/${id}`}
        className="text-sm text-[#466353] hover:text-[#173126] transition-colors mb-4"
      >
        返回球员档案
      </Link>

      <PlayerTabs playerId={id!} />

      <Card>
        <h3 className="text-lg font-semibold mb-4">
          转会记录
        </h3>

        {records.length === 0 ? (
          <p className="text-[#466353] text-center py-8">暂无转会记录</p>
        ) : (
          <div className="space-y-3">
            {records.map((record) => (
              <div
                key={record.record_id}
                className="flex flex-col md:flex-row md:items-center gap-4 p-4 bg-[#FFF8DC]/80 border border-[#1F5F43]/20"
              >
                <div className="flex items-center gap-3 md:w-48">
                  <span className={`text-sm font-medium ${TRANSFER_TYPE_COLORS[record.transfer_type] || 'text-[#173126]'}`}>
                    {TRANSFER_TYPE_NAMES[record.transfer_type] || record.transfer_type}
                  </span>
                </div>

                <div className="flex-1 flex flex-col md:flex-row md:items-center gap-2 md:gap-6">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-[#466353]">来自</span>
                    <Link
                      to={record.from_team_id ? `/teams/${record.from_team_id}` : '#'}
                      className={record.from_team_id ? 'text-[#1F5F43] hover:text-[#1F5F43] transition-colors' : 'text-[#466353]'}
                    >
                      {record.from_team_id ? '球队' : '无'}
                    </Link>
                  </div>

                  <div className="text-sm text-[#466353]">→</div>

                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-[#466353]">前往</span>
                    <Link
                      to={record.to_team_id ? `/teams/${record.to_team_id}` : '#'}
                      className={record.to_team_id ? 'text-[#1F5F43] hover:text-[#1F5F43] transition-colors' : 'text-[#466353]'}
                    >
                      {record.to_team_id ? '球队' : '无'}
                    </Link>
                  </div>
                </div>

                <div className="flex items-center gap-4 md:justify-end">
                  <div className="text-sm">
                    <span className="font-bold stat-number pixel-number text-[#173126]">
                      €{(record.amount / 1000000).toFixed(1)}M
                    </span>
                  </div>
                  <div className="text-xs text-[#466353]">
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
