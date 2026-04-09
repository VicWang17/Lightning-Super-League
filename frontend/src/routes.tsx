import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from './stores/auth'
import MainLayout from './components/layout/MainLayout'
import Home from './pages/Home/Index'
import Dashboard from './pages/Dashboard/Index'
import Login from './pages/Auth/Login'
import Register from './pages/Auth/Register'

// League Pages
import LeagueList from './pages/League/Index'
import LeagueDetail from './pages/League/Detail'

// Team Pages
import TeamDetail from './pages/Team/Detail'
import PlayerDetail from './pages/Team/PlayerDetail'

// Match Pages
const LiveMatch = () => <div>Live Match Page (待实现)</div>
const PreMatch = () => <div>Pre Match Page (待实现)</div>
const PostMatch = () => <div>Post Match Page (待实现)</div>
const Schedule = () => <div>Schedule Page (待实现)</div>

// Transfer Pages
const TransferMarket = () => <div>Transfer Market Page (待实现)</div>
const Watchlist = () => <div>Watchlist Page (待实现)</div>
const TransferHistory = () => <div>Transfer History Page (待实现)</div>

// 404 Page
const NotFound = () => (
  <div className="flex flex-col items-center justify-center min-h-[60vh]">
    <h1 className="text-6xl font-bold text-[#0D7377] mb-4">404</h1>
    <p className="text-[#8B8BA7] mb-6">页面未找到</p>
    <a href="/dashboard" className="text-[#0D7377] hover:underline">
      返回主页
    </a>
  </div>
)

// 路由守卫组件 - 需要登录
function RequireAuth() {
  const { isAuthenticated } = useAuthStore()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return <Outlet />
}

// 路由守卫组件 - 已登录用户不能访问（如登录页、注册页）
function RequireGuest() {
  const { isAuthenticated } = useAuthStore()
  
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }
  
  return <Outlet />
}

export const router = createBrowserRouter([
  // 公共页面
  {
    path: '/',
    element: <Home />,
  },
  
  // 访客专属页面（已登录用户不能访问）
  {
    element: <RequireGuest />,
    children: [
      {
        path: '/login',
        element: <Login />,
      },
      {
        path: '/register',
        element: <Register />,
      },
    ],
  },
  
  // 需要登录的页面
  {
    element: <RequireAuth />,
    children: [
      {
        path: '/',
        element: <MainLayout />,
        children: [
          {
            path: 'dashboard',
            element: <Dashboard />,
          },
          
          // 球队管理
          {
            path: 'team',
            children: [
              {
                path: 'players',
                element: <TeamDetail />,
              },
              {
                path: 'players/:id',
                element: <PlayerDetail />,
              },
              {
                path: 'tactics',
                element: <div>Tactics Page (待实现)</div>,
              },
              {
                path: 'training',
                element: <div>Training Page (待实现)</div>,
              },
            ],
          },
          
          // 球队详情 (公开访问)
          {
            path: 'teams/:id',
            element: <TeamDetail />,
          },
          
          // 球员详情 (公开访问)
          {
            path: 'players/:id',
            element: <PlayerDetail />,
          },
          
          // 比赛
          {
            path: 'match',
            children: [
              {
                path: 'live',
                element: <LiveMatch />,
              },
              {
                path: 'pre',
                element: <PreMatch />,
              },
              {
                path: 'post',
                element: <PostMatch />,
              },
              {
                path: 'schedule',
                element: <Schedule />,
              },
            ],
          },
          
          // 联赛
          {
            path: 'leagues',
            children: [
              {
                path: '',
                element: <LeagueList />,
              },
              {
                path: ':id',
                element: <LeagueDetail />,
              },
            ],
          },
          
          // 转会市场
          {
            path: 'transfer',
            children: [
              {
                path: 'market',
                element: <TransferMarket />,
              },
              {
                path: 'watchlist',
                element: <Watchlist />,
              },
              {
                path: 'history',
                element: <TransferHistory />,
              },
            ],
          },
        ],
      },
    ],
  },
  
  // 404
  {
    path: '*',
    element: <NotFound />,
  },
])

export default router
