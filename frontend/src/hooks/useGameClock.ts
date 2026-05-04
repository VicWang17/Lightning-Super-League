import { useState, useEffect, useRef, useCallback } from 'react'
import api from '../api/client'

interface ClockState {
  mode: string
  virtualNow: Date
  speed: number
  loading: boolean
  error: string | null
}

const SYNC_INTERVAL = 10000 // 每 10 秒同步一次后端
const TICK_INTERVAL = 1000   // 每秒更新显示

export function useGameClock(): ClockState {
  const [state, setState] = useState<ClockState>({
    mode: 'realtime',
    virtualNow: new Date(),
    speed: 1.0,
    loading: true,
    error: null,
  })

  // 用 ref 保存计算基准，避免闭包过时
  const baseRef = useRef<{
    virtualNow: Date
    localAt: number  // performance.now() 毫秒
    mode: string
    speed: number
  } | null>(null)

  const fetchClock = useCallback(async () => {
    try {
      const res = await api.getClock()
      const data = res.data
      const virtualNow = new Date(data.virtual_now)
      baseRef.current = {
        virtualNow,
        localAt: performance.now(),
        mode: data.mode,
        speed: data.speed,
      }
      setState(prev => ({
        ...prev,
        mode: data.mode,
        virtualNow,
        speed: data.speed,
        loading: false,
        error: null,
      }))
    } catch (err) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : '时钟同步失败',
      }))
    }
  }, [])

  // 首次加载
  useEffect(() => {
    fetchClock()
  }, [fetchClock])

  // 定时同步后端
  useEffect(() => {
    const id = setInterval(fetchClock, SYNC_INTERVAL)
    return () => clearInterval(id)
  }, [fetchClock])

  // 每秒本地插值更新显示
  useEffect(() => {
    const id = setInterval(() => {
      const base = baseRef.current
      if (!base) return

      const elapsedMs = performance.now() - base.localAt

      let nextDate: Date
      if (base.mode === 'realtime') {
        nextDate = new Date(base.virtualNow.getTime() + elapsedMs)
      } else if (base.mode === 'turbo') {
        nextDate = new Date(base.virtualNow.getTime() + elapsedMs * base.speed)
      } else {
        // step / paused: 不自动变化
        nextDate = base.virtualNow
      }

      setState(prev => ({
        ...prev,
        virtualNow: nextDate,
      }))
    }, TICK_INTERVAL)

    return () => clearInterval(id)
  }, [])

  return state
}
