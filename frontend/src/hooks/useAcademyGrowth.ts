import { useState, useEffect } from 'react'
import { api } from '../api/client'

export interface GrowthSnapshot {
  season_day: number
  ovr: number
  extra_data: Record<string, unknown> | null
  created_at: string
}

export function useAcademyGrowth(academyPlayerId: string | null) {
  const [data, setData] = useState<GrowthSnapshot[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!academyPlayerId) {
      setData([])
      return
    }

    let cancelled = false
    const fetch = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await api.getYouthGrowthCurve(academyPlayerId)
        if (!cancelled && res.success && res.data) {
          setData(res.data)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '获取成长曲线失败')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetch()
    return () => { cancelled = true }
  }, [academyPlayerId])

  return { data, loading, error }
}
