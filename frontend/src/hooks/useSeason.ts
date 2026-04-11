/**
 * 赛季状态管理 Hook
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import api from '../api/client'
import type { SeasonDetail, SeasonStatusForDisplay, Fixture } from '../types/season'

interface UseSeasonReturn {
  season: SeasonDetail | null
  displayStatus: SeasonStatusForDisplay | null
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

/**
 * 计算用于前端显示的赛季状态
 */
function calculateDisplayStatus(
  season: SeasonDetail | null,
  todayFixtures: Fixture[]
): SeasonStatusForDisplay | null {
  if (!season) return null

  const progressPercent = Math.round((season.current_day / season.total_days) * 100)
  
  // 分析今日比赛
  const hasLeague = todayFixtures.some(f => f.fixture_type === 'league')
  const hasCup = todayFixtures.some(f => 
    f.fixture_type.includes('cup_lightning') || f.fixture_type === 'cup_jenny'
  )
  
  // 获取联赛轮次
  const leagueFixture = todayFixtures.find(f => f.fixture_type === 'league')
  const leagueRound = leagueFixture?.round_number
  
  // 获取杯赛信息
  const cupFixture = todayFixtures.find(f => 
    f.fixture_type.includes('cup_lightning') || f.fixture_type === 'cup_jenny'
  )
  const cupRound = cupFixture?.round_number
  const cupStage = cupFixture?.cup_stage
  
  // 生成显示文本
  let displayText = ''
  if (season.status === 'finished') {
    displayText = `第${season.season_number}赛季 已结束`
  } else if (season.current_day === 0) {
    displayText = `第${season.season_number}赛季 即将开始`
  } else if (season.current_day >= season.offseason_start) {
    displayText = `第${season.season_number}赛季 休赛期 ${season.current_day}/${season.total_days}`
  } else if (hasLeague && hasCup) {
    displayText = `第${season.season_number}赛季 第${season.current_day}/${season.total_days}天 · 联赛${leagueRound}轮+杯赛`
  } else if (hasLeague) {
    displayText = `第${season.season_number}赛季 第${season.current_day}/${season.total_days}天 · 联赛第${leagueRound}轮`
  } else if (hasCup) {
    const stageText = cupStage === 'GROUP' ? '小组赛' : 
                      cupStage?.startsWith('ROUND_') ? `${cupStage.replace('ROUND_', '')}强` :
                      cupStage === 'QUARTER' ? '1/4决赛' :
                      cupStage === 'SEMI' ? '半决赛' :
                      cupStage === 'FINAL' ? '决赛' : '杯赛'
    displayText = `第${season.season_number}赛季 第${season.current_day}/${season.total_days}天 · ${stageText}`
  } else {
    displayText = `第${season.season_number}赛季 第${season.current_day}/${season.total_days}天`
  }

  return {
    season_number: season.season_number,
    current_day: season.current_day,
    total_days: season.total_days,
    progress_percent: progressPercent,
    has_league: hasLeague,
    has_cup: hasCup,
    league_round: leagueRound,
    cup_round: cupRound,
    cup_stage: cupStage,
    total_fixtures_today: todayFixtures.length,
    display_text: displayText,
  }
}

export function useSeason(): UseSeasonReturn {
  const [season, setSeason] = useState<SeasonDetail | null>(null)
  const [todayFixtures, setTodayFixtures] = useState<Fixture[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchSeasonData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      // 获取当前赛季
      console.log('Fetching current season...')
      const seasonResponse = await api.getCurrentSeason()
      console.log('Season response:', seasonResponse)
      
      // 后端统一返回 {success, data} 格式
      if (!seasonResponse.success || !seasonResponse.data) {
        throw new Error('获取赛季信息失败')
      }
      setSeason(seasonResponse.data)

      // 获取今日比赛
      if (seasonResponse.data.season_number) {
        try {
          const fixturesResponse = await api.getTodayFixtures(seasonResponse.data.season_number)
          // 后端统一返回 {success, data} 格式
          if (fixturesResponse.success && fixturesResponse.data) {
            setTodayFixtures(fixturesResponse.data.fixtures)
          } else {
            setTodayFixtures([])
          }
        } catch (err) {
          console.log('今日比赛获取失败:', err)
          // 今日比赛获取失败不影响整体显示
          setTodayFixtures([])
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSeasonData()
  }, [fetchSeasonData])

  const displayStatus = useMemo(() => {
    return calculateDisplayStatus(season, todayFixtures)
  }, [season, todayFixtures])

  return {
    season,
    displayStatus,
    loading,
    error,
    refresh: fetchSeasonData,
  }
}

/**
 * 获取赛季日历
 */
export function useSeasonCalendar(seasonNumber: number, teamId?: string) {
  const [calendar, setCalendar] = useState<unknown[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchCalendar() {
      try {
        setLoading(true)
        const response = await api.getSeasonCalendar(seasonNumber, teamId)
        // 后端统一返回 {success, data} 格式
        if (response.success && response.data) {
          setCalendar(response.data.calendar || [])
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '未知错误')
      } finally {
        setLoading(false)
      }
    }

    if (seasonNumber) {
      fetchCalendar()
    }
  }, [seasonNumber, teamId])

  return { calendar, loading, error }
}

/**
 * 获取球队赛程
 */
export function useTeamFixtures(seasonNumber: number, teamId: string, fixtureType?: string) {
  const [fixtures, setFixtures] = useState<unknown[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchFixtures() {
      try {
        setLoading(true)
        const response = await api.getTeamFixtures(seasonNumber, teamId, fixtureType)
        // 后端统一返回 {success, data} 格式
        if (response.success && response.data) {
          setFixtures(response.data.fixtures || [])
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '未知错误')
      } finally {
        setLoading(false)
      }
    }

    if (seasonNumber && teamId) {
      fetchFixtures()
    }
  }, [seasonNumber, teamId, fixtureType])

  return { fixtures, loading, error }
}
