import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { TeamHonorsResponse } from '../types/world'
import type { RecordsByCategory } from '../types/records'
import type { TeamHistoryResponse } from '../types/records'

export function useTeamHistory(teamId: string | undefined) {
  const [history, setHistory] = useState<TeamHistoryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!teamId) {
      setLoading(false)
      return
    }

    const fetchHistory = async () => {
      try {
        setLoading(true)
        const response = await api.get<TeamHistoryResponse>(`/teams/${teamId}/history`)
        if (response.success) {
          setHistory(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取球队历史失败')
      } finally {
        setLoading(false)
      }
    }

    fetchHistory()
  }, [teamId])

  return { history, loading, error }
}

export function useTeamHonors(teamId: string | undefined) {
  const [honors, setHonors] = useState<TeamHonorsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!teamId) {
      setLoading(false)
      return
    }

    const fetchHonors = async () => {
      try {
        setLoading(true)
        const response = await api.get<TeamHonorsResponse>(`/teams/${teamId}/honors`)
        if (response.success) {
          setHonors(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取球队荣誉失败')
      } finally {
        setLoading(false)
      }
    }

    fetchHonors()
  }, [teamId])

  return { honors, loading, error }
}

export function useTeamRecords(teamId: string | undefined) {
  const [records, setRecords] = useState<RecordsByCategory | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!teamId) {
      setLoading(false)
      return
    }

    const fetchRecords = async () => {
      try {
        setLoading(true)
        const response = await api.get<RecordsByCategory>(`/teams/${teamId}/records`)
        if (response.success) {
          setRecords(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取球队纪录失败')
      } finally {
        setLoading(false)
      }
    }

    fetchRecords()
  }, [teamId])

  return { records, loading, error }
}
