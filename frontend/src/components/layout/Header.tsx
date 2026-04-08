import { Bell, Settings, Search } from 'lucide-react'

function Header() {
  return (
    <header className="h-16 bg-[#0A0A0F]/80 backdrop-blur-xl border-b border-[#2D2D44] flex items-center justify-between px-6 sticky top-0 z-40">
      {/* Left - Search */}
      <div className="flex items-center gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#4B4B6A]" />
          <input 
            type="text" 
            placeholder="搜索球员、球队..."
            className="w-64 bg-[#12121A] border border-[#2D2D44] rounded-lg pl-10 pr-4 py-2 text-sm text-[#E2E2F0] placeholder:text-[#4B4B6A] focus:outline-none focus:border-[#0D7377]/50 transition-colors"
          />
        </div>
      </div>
      
      {/* Right */}
      <div className="flex items-center gap-6">
        {/* Season Info */}
        <div className="text-right">
          <p className="text-xs text-[#4B4B6A] uppercase tracking-wider">赛季 1 · 第 3 轮</p>
          <p className="text-sm font-medium">2024/25</p>
        </div>

        {/* Divider */}
        <div className="w-px h-8 bg-[#2D2D44]" />

        {/* Funds */}
        <div className="text-right">
          <p className="text-xs text-[#4B4B6A]">球队资金</p>
          <p className="text-lg font-semibold stat-number text-white">€ 10.5M</p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button className="w-9 h-9 rounded-lg bg-[#12121A] border border-[#2D2D44] hover:border-[#0D7377]/50 flex items-center justify-center text-[#8B8BA7] hover:text-white transition-colors">
            <Bell className="w-4 h-4" />
          </button>
          <button className="w-9 h-9 rounded-lg bg-[#12121A] border border-[#2D2D44] hover:border-[#0D7377]/50 flex items-center justify-center text-[#8B8BA7] hover:text-white transition-colors">
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  )
}

export default Header
