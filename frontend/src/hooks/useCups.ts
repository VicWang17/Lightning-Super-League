import { useState, useEffect } from 'react'
import api from '../api/client'
import type { CupCompetition, CupDetail, CupGroup, CupFixture } from '../types/cup'

// 获取当前赛季的所有杯赛
export function useCups() {
  const [cups, setCups] = useState<CupCompetition[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchCups = async () => {
      try {
        setLoading(true)
        const response = await api.get<CupCompetition[]>('/cups')
        if (response.success) {
          setCups(response.data)
        } else {
          setError(response.message || '获取杯赛列表失败')
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取杯赛列表失败')
      } finally {
        setLoading(false)
      }
    }

    fetchCups()
  }, [])

  return { cups, loading, error }
}

// 获取杯赛详情
export function useCupDetail(cupId: string | undefined) {
  const [cup, setCup] = useState<CupDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!cupId) {
      setLoading(false)
      setError('杯赛ID不能为空')
      return
    }

    const fetchCupDetail = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await api.get<CupDetail>(`/cups/${cupId}`)
        if (response.success) {
          setCup(response.data)
        } else {
          setError(response.message || '获取杯赛详情失败')
          setCup(null)
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : '获取杯赛详情失败'
        setError(errorMsg)
        setCup(null)
      } finally {
        setLoading(false)
      }
    }

    fetchCupDetail()
  }, [cupId])

  return { cup, loading, error }
}

// 获取杯赛小组赛分组
export function useCupGroups(cupId: string | undefined) {
  const [groups, setGroups] = useState<CupGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!cupId) {
      setLoading(false)
      return
    }

    const fetchGroups = async () => {
      try {
        setLoading(true)
        const response = await api.get<CupGroup[]>(`/cups/${cupId}/groups`)
        if (response.success) {
          setGroups(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取小组赛分组失败')
      } finally {
        setLoading(false)
      }
    }

    fetchGroups()
  }, [cupId])

  return { groups, loading, error }
}

// 获取杯赛赛程
export function useCupFixtures(cupId: string | undefined, stage?: string) {
  const [fixtures, setFixtures] = useState<CupFixture[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!cupId) {
      setLoading(false)
      return
    }

    const fetchFixtures = async () => {
      try {
        setLoading(true)
        let url = `/cups/${cupId}/fixtures`
        if (stage) url += `?stage=${stage}`
        const response = await api.get<CupFixture[]>(url)
        if (response.success) {
          setFixtures(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取杯赛赛程失败')
      } finally {
        setLoading(false)
      }
    }

    fetchFixtures()
  }, [cupId, stage])

  return { fixtures, loading, error }
}

// 获取淘汰赛对阵
export function useCupKnockoutBracket(cupId: string | undefined) {
  const [bracket, setBracket] = useState<{
    round_of_16?: CupFixture[]
    quarter_finals?: CupFixture[]
    semi_finals?: CupFixture[]
    final?: CupFixture[]
  }>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!cupId) {
      setLoading(false)
      return
    }

    const fetchBracket = async () => {
      try {
        setLoading(true)
        const response = await api.get<{
          round_of_16: CupFixture[]
          quarter_finals: CupFixture[]
          semi_finals: CupFixture[]
          final: CupFixture[]
        }>(`/cups/${cupId}/bracket`)
        if (response.success) {
          setBracket(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取淘汰赛对阵失败')
      } finally {
        setLoading(false)
      }
    }

    fetchBracket()
  }, [cupId])

  return { bracket, loading, error }
}

// 获取用户球队参加的杯赛
export function useMyTeamCup() {
  const [myCup, setMyCup] = useState<CupCompetition | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchMyTeamCup = async () => {
      try {
        setLoading(true)
        const response = await api.get<CupCompetition>('/cups/my-team')
        if (response.success && response.data) {
          setMyCup(response.data)
        }
      } catch {
        // 用户可能没有参加杯赛，这是正常的
        console.log('[useMyTeamCup] 用户没有参加杯赛或获取失败')
      } finally {
        setLoading(false)
      }
    }

    fetchMyTeamCup()
  }, [])

  return { myCup, loading }
}
