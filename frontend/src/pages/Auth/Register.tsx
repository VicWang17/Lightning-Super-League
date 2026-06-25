import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'

export default function Register() {
  const navigate = useNavigate()
  return (
    <div className="fresh-auth-shell min-h-screen flex items-center justify-center px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full">
        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-8"
        >
          <Link to="/" className="inline-block group">
            <img 
              src="/logo.png" 
              alt="闪电超级联赛"
              className="h-14 w-auto object-contain"
            />
          </Link>
        </motion.div>

        {/* Not Implemented Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="fresh-auth-card p-8 text-center hover:-translate-x-0.5 hover:-translate-y-0.5 transition-transform"
        >
          {/* Title */}
          <h1 className="text-2xl font-black text-[#173126] mb-3">
            接口未实现
          </h1>

          {/* Description */}
          <p className="font-semibold text-[#466353] mb-8 leading-relaxed">
            注册功能正在开发中，敬请期待。
            <br />
            目前请使用测试账号登录体验游戏。
          </p>

          {/* Divider */}
          <div className="border-t-2 border-[#1F5F43]/25 pt-6 mb-6">
            <p className="text-sm font-bold text-[#466353] mb-4">开发环境测试账号</p>
            <div className="bg-white/70 border-2 border-[#1F5F43]/30 p-4 text-left space-y-2">
              <div className="flex justify-between text-sm">
                <span className="font-semibold text-[#466353]">邮箱：</span>
                <span className="font-black text-[#173126]">ai_east_l1_1_001@lightning.dev</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="font-semibold text-[#466353]">密码：</span>
                <span className="font-black text-[#173126]">ai_password</span>
              </div>
            </div>
          </div>

          {/* Buttons */}
          <div className="space-y-3">
            <Link
              to="/login"
              className="fresh-public-button inline-flex items-center justify-center gap-2 w-full px-6 py-3"
            >
              前往登录
            </Link>
            
            <button
              onClick={() => navigate(-1)}
              className="inline-flex items-center justify-center gap-2 w-full px-6 py-3 text-[#466353] hover:text-[#173126] font-black transition-colors"
            >
              返回上一页
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
