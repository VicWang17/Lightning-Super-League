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

// Cup Pages
import CupList from './pages/Cup/Index'
import CupDetail from './pages/Cup/Detail'

// Team Pages
import TeamDetail from './pages/Team/Detail'
import PlayerDetail from './pages/Team/PlayerDetail'
import Tactics from './pages/Team/Tactics'

// Training Pages
import TrainingWeekly from './pages/Training/Weekly'
import TrainingCalendar from './pages/Training/Calendar'
import PlayerFatigue from './pages/Training/Fatigue'
import TrainingHistory from './pages/Training/History'

// Match Pages
import Schedule from './pages/Match/Schedule'
import PreMatch from './pages/Match/PreMatch'
import LiveMatch from './pages/Match/LiveMatch'
import PostMatch from './pages/Match/PostMatch'

// Transfer Pages
import TransferMarket from './pages/Transfer/Market'
import FreeMarket from './pages/Transfer/FreeMarket'
import Watchlist from './pages/Transfer/Watchlist'
import MyListings from './pages/Transfer/MyListings'
import TransferHistory from './pages/Transfer/History'

// Youth Pages
import YouthAcademy from './pages/Youth/Academy'
import Draft from './pages/Youth/Draft'
import YoungPlayers from './pages/Youth/YoungPlayers'

// Finance Pages
import FinanceOverview from './pages/Finance/Overview'
import BudgetPlanning from './pages/Finance/BudgetPlanning'
import IncomeDetails from './pages/Finance/Income'
import ExpenseDetails from './pages/Finance/Expense'

// 404 Page
const NotFound = () => (
  <div className="flex flex-col items-center justify-center min-h-[60vh]">
    <h1 className="text-6xl font-bold text-[#0D7377] mb-4 pixel-title">404</h1>
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
                element: <Tactics />,
              },
              {
                path: 'training',
                element: <Navigate to="/training/weekly" replace />,
              },
            ],
          },
          
          // 训练系统
          {
            path: 'training',
            children: [
              {
                path: 'weekly',
                element: <TrainingWeekly />,
              },
              {
                path: 'calendar',
                element: <TrainingCalendar />,
              },
              {
                path: 'fatigue',
                element: <PlayerFatigue />,
              },
              {
                path: 'history',
                element: <TrainingHistory />,
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
                path: 'all',
                element: <LeagueList />,
              },
              {
                path: ':id',
                element: <LeagueDetail />,
              },
            ],
          },
          
          // 杯赛
          {
            path: 'cups',
            children: [
              {
                path: '',
                element: <CupList />,
              },
              {
                path: 'all',
                element: <CupList />,
              },
              {
                path: ':id',
                element: <CupDetail />,
              },
            ],
          },
          
          // 所有比赛（联赛+杯赛汇总）
          {
            path: 'competitions',
            element: <LeagueList />,
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
                path: 'free-market',
                element: <FreeMarket />,
              },
              {
                path: 'watchlist',
                element: <Watchlist />,
              },
              {
                path: 'my-listings',
                element: <MyListings />,
              },
              {
                path: 'history',
                element: <TransferHistory />,
              },
            ],
          },
          
          // 青训系统
          {
            path: 'youth',
            children: [
              {
                path: '',
                element: <YouthAcademy />,
              },
              {
                path: 'academy',
                element: <YouthAcademy />,
              },
              {
                path: 'draft',
                element: <Draft />,
              },
              {
                path: 'young-players',
                element: <YoungPlayers />,
              },
            ],
          },
          
          // 财务中心
          {
            path: 'finance',
            children: [
              {
                path: '',
                element: <FinanceOverview />,
              },
              {
                path: 'overview',
                element: <FinanceOverview />,
              },
              {
                path: 'budget',
                element: <BudgetPlanning />,
              },
              {
                path: 'income',
                element: <IncomeDetails />,
              },
              {
                path: 'expense',
                element: <ExpenseDetails />,
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
