import { useAuthStore } from '../stores/auth'

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

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`
    
    // 获取 token
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

    if (!response.ok) {
      throw new Error(data.detail || data.message || '请求失败')
    }

    return data
  }

  // Auth API
  async login(credentials: LoginCredentials) {
    const formData = new URLSearchParams()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)

    return this.request<UserWithToken>('/auth/login', {
      method: 'POST',
      body: formData,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
  }

  async logout() {
    return this.request<void>('/auth/logout', {
      method: 'POST',
    })
  }

  async getCurrentUser() {
    return this.request<User>('/auth/me', {
      method: 'GET',
    })
  }

  async refreshToken(refreshToken: string) {
    return this.request<TokenData>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  // GET helper
  async get<T>(endpoint: string, options: RequestInit = {}) {
    return this.request<T>(endpoint, { ...options, method: 'GET' })
  }

  // POST helper
  async post<T>(endpoint: string, body: unknown, options: RequestInit = {}) {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(body),
      headers: {
        'Content-Type': 'application/json',
        ...((options.headers as Record<string, string>) || {}),
      },
    })
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

interface UserWithToken extends User {
  token: TokenData
}

export const api = new ApiClient(API_BASE_URL)
export default api
