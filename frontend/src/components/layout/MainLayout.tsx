import { Outlet, useLocation } from 'react-router-dom'
import Header from './Header'
import TopNav from './TopNav'

function getPageBackground(pathname: string) {
  if (pathname === '/dashboard') return 'dashboard'
  if (pathname.startsWith('/mail')) return 'inbox'
  if (/^\/team\/players\/[^/]+/.test(pathname) || /^\/players\/[^/]+/.test(pathname)) return 'player-detail'
  if (pathname.startsWith('/team/tactics')) return 'tactics'
  if (pathname.startsWith('/team') || pathname.startsWith('/players')) return 'locker'
  if (pathname.startsWith('/match')) return 'match'
  if (pathname.startsWith('/training')) return 'training'
  if (pathname.startsWith('/leagues') || pathname.startsWith('/competitions')) return 'league'
  if (pathname.startsWith('/cups')) return 'cup'
  if (pathname.startsWith('/transfer')) return 'transfer'
  if (pathname.startsWith('/youth')) return 'youth'
  if (pathname.startsWith('/finance')) return 'finance'
  if (pathname.startsWith('/world')) return 'world'
  return 'default'
}

function MainLayout() {
  const location = useLocation()
  const pageBackground = getPageBackground(location.pathname)

  return (
    <div className="min-h-screen flex flex-col game-shell" data-page-bg={pageBackground}>
      {/* Top Command Bar */}
      <Header />

      {/* Navigation Tab Bar */}
      <TopNav />

      {/* Main Content */}
      <main className="game-main flex-1 overflow-auto">
        <div className="max-w-[1400px] mx-auto p-5 lg:p-7">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export default MainLayout
