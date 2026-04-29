import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Zap, Mail, Lock, Eye, EyeOff, AlertCircle } from 'lucide-react'
import { useAuthStore } from '../../stores/auth'
import { api } from '../../api/client'
import Input from '../../components/ui/Input'
import Button from '../../components/ui/Button'

export default function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { setUser } = useAuthStore()
  
  // 获取 redirect 参数，如果没有则默认跳转到 dashboard
  const redirectTo = searchParams.get('redirect') || '/dashboard'
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      const response = await api.login({
        username: formData.email,
        password: formData.password,
      })

      if (response.success && response.data) {
        setUser(response.data)
        navigate(redirectTo)
      } else {
        setError(response.message || '登录失败')
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '登录失败，请检查邮箱和密码'
      setError(errorMessage)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

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
            <div className="w-12 h-12 bg-[#0D7377] flex items-center justify-center shadow-glow-green group-hover:shadow-glow-green transition-shadow duration-300">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-white">闪电超级联赛</span>
          </Link>
          <p className="mt-4 text-[#8B8BA7]">登录你的足球经理账号</p>
        </motion.div>

        {/* Login Form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="bg-[#12121A] border-2 border-[#2D2D44] p-8 shadow-pixel-lg hover:-translate-x-0.5 hover:-translate-y-0.5 transition-transform"
        >
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mb-6 p-4 bg-[#EF4444]/10 border-2 border-[#EF4444]/30 flex items-center gap-3"
            >
              <AlertCircle className="w-5 h-5 text-[#EF4444] flex-shrink-0" />
              <p className="text-sm text-[#EF4444]">{error}</p>
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <Input
                type="email"
                name="email"
                label="邮箱地址"
                placeholder="请输入邮箱地址"
                value={formData.email}
                onChange={handleChange}
                leftIcon={<Mail className="w-5 h-5" />}
                required
                fullWidth
              />
            </div>

            <div>
              <Input
                type={showPassword ? 'text' : 'password'}
                name="password"
                label="密码"
                placeholder="请输入密码"
                value={formData.password}
                onChange={handleChange}
                leftIcon={<Lock className="w-5 h-5" />}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="text-[#8B8BA7] hover:text-[#E2E2F0] transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                }
                required
                fullWidth
              />
            </div>

            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="checkbox"
                  className="w-4 h-4 border-2 border-[#2D2D44] bg-[#0A0A0F] text-[#0D7377] focus:ring-[#0D7377]/20"
                />
                <span className="text-[#8B8BA7] group-hover:text-[#E2E2F0] transition-colors">
                  记住我
                </span>
              </label>
              <Link
                to="#"
                className="text-[#0D7377] hover:text-[#0D7377] transition-colors"
              >
                忘记密码？
              </Link>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              fullWidth
              isLoading={isSubmitting}
            >
              登录
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-[#8B8BA7]">
              还没有账号？{' '}
              <Link
                to="/register"
                className="text-[#0D7377] hover:text-[#0D7377] font-medium transition-colors"
              >
                立即注册
              </Link>
            </p>
          </div>
        </motion.div>

        {/* Back to Home */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-8 text-center"
        >
          <Link
            to="/"
            className="text-sm text-[#4B4B6A] hover:text-[#8B8BA7] transition-colors"
          >
            ← 返回首页
          </Link>
        </motion.div>

        {/* Demo hint */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="mt-6 p-4 bg-[#0D7377]/10 border-2 border-[#0D7377]/30"
        >
          <p className="text-xs text-[#8B8BA7] text-center">
            <span className="text-[#0D7377] font-medium">测试账号：</span>
            <br />
            邮箱: ai_east_1_1@ai.com
            <br />
            密码: ai_password
          </p>
        </motion.div>
      </div>
    </div>
  )
}
