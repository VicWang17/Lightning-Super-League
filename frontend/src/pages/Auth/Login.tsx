import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Eye, EyeOff } from '../../components/ui/pixel-icons'
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
          <p className="mt-4 font-bold text-[#466353]">登录你的足球经理账号</p>
        </motion.div>

        {/* Login Form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="fresh-auth-card p-8 hover:-translate-x-0.5 hover:-translate-y-0.5 transition-transform"
        >
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mb-6 p-4 bg-[#FF6F59]/15 border-2 border-[#FF6F59]/45"
            >
              <p className="text-sm font-bold text-[#FF6F59]">{error}</p>
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
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                  className="text-[#466353] hover:text-[#173126] transition-colors"
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
                  className="w-4 h-4 border-2 border-[#1F5F43] bg-white text-[#59C7EE] focus:ring-[#59C7EE]/20"
                />
                <span className="font-semibold text-[#466353] group-hover:text-[#173126] transition-colors">
                  记住我
                </span>
              </label>
              <Link
                to="#"
                className="font-bold text-[#1F5F43] hover:text-[#1F5F43] transition-colors"
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
            <p className="font-semibold text-[#466353]">
              还没有账号？{' '}
              <Link
                to="/register"
                className="text-[#1F5F43] hover:text-[#1F5F43] font-black transition-colors"
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
          <button
            onClick={() => navigate(-1)}
            className="text-sm font-bold text-[#466353] hover:text-[#173126] transition-colors"
          >
            ← 返回上一页
          </button>
        </motion.div>

        {/* Demo hint */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="mt-6 p-4 bg-white/70 border-2 border-[#1F5F43]/30 shadow-[4px_4px_0_rgba(31,95,67,0.12)]"
        >
          <p className="text-xs font-semibold text-[#466353] text-center">
            <span className="text-[#1F5F43] font-black">测试账号：</span>
            <br />
            邮箱: ai_east_l1_1_001@lightning.dev
            <br />
            密码: ai_password
          </p>
        </motion.div>
      </div>
    </div>
  )
}
