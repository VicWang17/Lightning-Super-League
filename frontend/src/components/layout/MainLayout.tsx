import { Outlet } from 'react-router-dom'
import Header from './Header'
import TopNav from './TopNav'

function MainLayout() {
  return (
    <div className="min-h-screen flex flex-col game-shell">
      {/* Top Command Bar */}
      <Header />

      {/* Navigation Tab Bar */}
      <TopNav />

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-[1400px] mx-auto p-5 lg:p-7">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export default MainLayout
