import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Zap, Tools as Construction, ArrowLeft } from '../../components/ui/pixel-icons'

export default function Register() {
  return (
    <div className="min-h-screen bg-[#0A0A0F] flex items-center justify-center px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full">
        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-8"
        >
          <Link to="/" className="inline-flex items-center gap-3 group">
            <div className="w-12 h-12 bg-[#0D7377] flex items-center justify-center border-2 border-transparent shadow-glow-green group-hover:shadow-glow-green transition-shadow duration-300">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-white">闪电超级联赛</span>
          </Link>
        </motion.div>

        {/* Not Implemented Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="bg-[#12121A] border-2 border-[#2D2D44] p-8 shadow-pixel-lg text-center hover:-translate-x-0.5 hover:-translate-y-0.5 transition-transform"
        >
          {/* Icon */}
          <div className="w-20 h-20 mx-auto mb-6 rounded-none bg-[#0D4A4D]/40 border-2 border-[#0D7377]/30 flex items-center justify-center">
            <Construction className="w-10 h-10 text-[#0D7377]" />
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-white mb-3">
            接口未实现
          </h1>

          {/* Description */}
          <p className="text-[#8B8BA7] mb-8 leading-relaxed">
            注册功能正在开发中，敬请期待。
            <br />
            目前请使用测试账号登录体验游戏。
          </p>

          {/* Divider */}
          <div className="border-t-2 border-[#2D2D44] pt-6 mb-6">
            <p className="text-sm text-[#4B4B6A] mb-4">开发环境测试账号</p>
            <div className="bg-[#0A0A0F] border-2 border-[#2D2D44] p-4 text-left space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-[#8B8BA7]">邮箱：</span>
                <span className="text-[#E2E2F0]">ai_east_l1_001@lightning.dev</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[#8B8BA7]">密码：</span>
                <span className="text-[#E2E2F0]">ai_password</span>
              </div>
            </div>
          </div>

          {/* Buttons */}
          <div className="space-y-3">
            <Link
              to="/login"
              className="inline-flex items-center justify-center gap-2 w-full px-6 py-3 bg-[#0D7377] hover:bg-[#0A5A5D] text-white font-bold border-2 border-transparent transition-all duration-200 shadow-pixel-green hover:-translate-x-0.5 hover:-translate-y-0.5"
            >
              前往登录
            </Link>
            
            <Link
              to="/"
              className="inline-flex items-center justify-center gap-2 w-full px-6 py-3 text-[#8B8BA7] hover:text-[#E2E2F0] font-medium transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              返回首页
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
