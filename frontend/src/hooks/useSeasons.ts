import { useState, useEffect } from 'react'
import api from '../api/client'
import type { Season } from '../types/season'

export function useSeasons() {
  const [seasons, setSeasons] = useState<Season[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchSeasons = async () => {
      try {
        setLoading(true)
        const response = await api.get<Season[]>('/seasons')
        if (response.success) {
          setSeasons(response.data)
        } else {
          setError(response.message || '获取赛季列表失败')
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取赛季列表失败')
      } finally {
        setLoading(false)
      }
    }

    fetchSeasons()
  }, [])

  return { seasons, loading, error }
}
