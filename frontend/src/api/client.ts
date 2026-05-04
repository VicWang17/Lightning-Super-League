import { useAuthStore } from '../stores/auth'
import type { Season, SeasonDetail, TodayFixturesResponse, SeasonCalendarResponse } from '../types/season'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

interface ApiResponse<T = unknown> {
  success: boolean
  message: string
  data: T
}

interface LoginCredentials {
  username: string
  password: string
}

class ApiClient {
  private baseUrl: string
  private isRefreshing = false
  private refreshPromise: Promise<boolean> | null = null

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  private async requestWithAuth<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`
    
    // 获取当前 token
    const token = useAuthStore.getState().token
    
    const headers: Record<string, string> = {
      'Accept': 'application/json',
      ...((options.method === 'POST' || options.method === 'PUT') && !(options.body instanceof FormData)
        ? { 'Content-Type': 'application/x-www-form-urlencoded' }
        : {}),
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...((options.headers as Record<string, string>) || {}),
    }

    const config: RequestInit = {
      ...options,
      headers,
    }

    const response = await fetch(url, config)
    const data = await response.json()

    // 处理 401 错误 - token 过期
    if (response.status === 401) {
      console.log(`[API] 401 Unauthorized for ${endpoint}, attempting token refresh...`)
      
      // 尝试刷新 token
      const refreshed = await this.tryRefreshToken()
      
      if (refreshed) {
        // 刷新成功，使用新 token 重试原请求
        console.log(`[API] Token refreshed, retrying ${endpoint}...`)
        return this.retryRequest<T>(endpoint, options)
      } else {
        // 刷新失败，跳转到登录页
        console.log('[API] Token refresh failed, redirecting to login...')
        this.redirectToLogin()
        throw new Error('登录已过期，请重新登录')
      }
    }

    if (!response.ok) {
      throw new Error(data.detail || data.message || '请求失败')
    }

    return data
  }

  // 使用新 token 重试请求
  private async retryRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`
    const newToken = useAuthStore.getState().token
    
    const headers: Record<string, string> = {
      'Accept': 'application/json',
      ...((options.method === 'POST' || options.method === 'PUT') && !(options.body instanceof FormData)
        ? { 'Content-Type': 'application/x-www-form-urlencoded' }
        : {}),
      ...(newToken ? { 'Authorization': `Bearer ${newToken}` } : {}),
      ...((options.headers as Record<string, string>) || {}),
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })
    
    const data = await response.json()
    
    if (!response.ok) {
      throw new Error(data.detail || data.message || '请求失败')
    }

    return data
  }

  // 尝试刷新 token（带锁，防止并发刷新）
  private async tryRefreshToken(): Promise<boolean> {
    // 如果正在刷新，等待当前刷新完成
    if (this.isRefreshing && this.refreshPromise) {
      console.log('[API] Waiting for existing token refresh...')
      return this.refreshPromise
    }

    // 开始新的刷新流程
    this.isRefreshing = true
    this.refreshPromise = this.doRefreshToken()

    try {
      const result = await this.refreshPromise
      return result
    } finally {
      this.isRefreshing = false
      this.refreshPromise = null
    }
  }

  // 执行实际的 token 刷新
  private async doRefreshToken(): Promise<boolean> {
    const refreshToken = useAuthStore.getState().refreshToken
    
    if (!refreshToken) {
      console.log('[API] No refresh token available')
      return false
    }

    try {
      console.log('[API] Refreshing token...')
      
      const response = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })

      if (!response.ok) {
        console.log('[API] Token refresh failed:', response.status)
        return false
      }

      const data = await response.json()
      
      if (!data.success || !data.data) {
        console.log('[API] Token refresh failed:', data.message)
        return false
      }

      // 更新 store 中的 token
      const tokenData = data.data
      useAuthStore.getState().setToken(tokenData)
      
      console.log('[API] Token refreshed successfully')
      return true
      
    } catch (error) {
      console.error('[API] Token refresh error:', error)
      return false
    }
  }

  // 跳转到登录页
  private redirectToLogin() {
    // 清除登录状态
    useAuthStore.getState().logout()
    
    // 跳转到登录页（保留当前路径，登录后可以返回）
    const currentPath = window.location.pathname
    if (currentPath !== '/login') {
      window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`
    }
  }

  // Auth API
  async login(credentials: LoginCredentials) {
    const formData = new URLSearchParams()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)

    const url = `${this.baseUrl}/auth/login`
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
      },
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || data.message || '登录失败')
    }

    return data
  }

  async logout() {
    return this.requestWithAuth<void>('/auth/logout', {
      method: 'POST',
    })
  }

  async getCurrentUser() {
    return this.requestWithAuth<User>('/auth/me', {
      method: 'GET',
    })
  }

  async refreshToken(refreshToken: string) {
    return this.requestWithAuth<TokenData>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  // GET helper
  async get<T>(endpoint: string, options: RequestInit = {}) {
    return this.requestWithAuth<T>(endpoint, { ...options, method: 'GET' })
  }

  // POST helper
  async post<T>(endpoint: string, body: unknown, options: RequestInit = {}) {
    return this.requestWithAuth<T>(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(body),
      headers: {
        'Content-Type': 'application/json',
        ...((options.headers as Record<string, string>) || {}),
      },
    })
  }

  // ==================== 赛季 API ====================
  
  async getSeasons() {
    return this.requestWithAuth<Season[]>('/seasons', { method: 'GET' })
  }

  async getCurrentSeason() {
    return this.requestWithAuth<SeasonDetail>('/seasons/current', { method: 'GET' })
  }

  async getSeasonByNumber(seasonNumber: number) {
    return this.requestWithAuth<SeasonDetail>(`/seasons/${seasonNumber}`, { method: 'GET' })
  }

  async createSeason(startDate?: string) {
    return this.requestWithAuth<Season>('/seasons', {
      method: 'POST',
      body: startDate ? JSON.stringify({ start_date: startDate }) : undefined,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  async startSeason(seasonNumber: number) {
    return this.requestWithAuth<Season>(`/seasons/${seasonNumber}/start`, { method: 'POST' })
  }

  async processNextDay(seasonNumber: number) {
    return this.requestWithAuth<{
      season_number: number
      current_day: number
      status: string
      fixtures_processed: number
      results: unknown[]
    }>(`/seasons/${seasonNumber}/next-day`, { method: 'POST' })
  }

  async getTodayFixtures(seasonNumber: number) {
    return this.requestWithAuth<TodayFixturesResponse>(`/seasons/${seasonNumber}/today`, { method: 'GET' })
  }

  async getSeasonCalendar(seasonNumber: number, teamId?: string) {
    const query = teamId ? `?team_id=${teamId}` : ''
    return this.requestWithAuth<SeasonCalendarResponse>(`/seasons/${seasonNumber}/calendar${query}`, { method: 'GET' })
  }

  async getTeamFixtures(seasonNumber: number, teamId: string, fixtureType?: string) {
    const query = fixtureType ? `?fixture_type=${fixtureType}` : ''
    return this.requestWithAuth<{ season_number: number; team_id: string; fixtures: unknown[] }>(
      `/seasons/${seasonNumber}/teams/${teamId}/fixtures${query}`,
      { method: 'GET' }
    )
  }

  // ==================== 时钟 API ====================
  async getClock() {
    // 时钟接口不需要认证
    const url = `${this.baseUrl}/clock`
    const response = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    })
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || data.message || '获取时钟失败')
    }
    return data as {
      success: boolean
      data: {
        mode: string
        virtual_now: string
        speed: number
      }
    }
  }
}

// Types needed for the API client
interface User {
  id: string
  username: string
  email: string
  nickname: string | null
  avatar_url: string | null
  level: number
  experience: number
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login: string | null
}

interface TokenData {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export const api = new ApiClient(API_BASE_URL)
export default api
