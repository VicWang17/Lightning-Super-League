import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'

function MainLayout() {
  return (
    <div className="min-h-screen flex pixel-grid-bg">
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default MainLayout
