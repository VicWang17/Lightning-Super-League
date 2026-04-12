import { useEffect, useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, useScroll, useTransform } from 'framer-motion'
import { Trophy, Users, Shield, Swords, Zap } from 'lucide-react'
import { useAuthStore } from '../../stores/auth'

// 动画配置
const fadeInUp = {
  initial: { opacity: 0, y: 40 },
  animate: { opacity: 1, y: 0 }
}

const fadeInUpTransition = { duration: 0.8, ease: [0.22, 1, 0.36, 1] }

const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 }
}

const fadeInTransition = { duration: 1.2 }

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
}

// 核心玩法
const features = [
  {
    icon: Trophy,
    title: '联赛征程',
    desc: '从业余联赛起步，一路征战顶级联赛',
  },
  {
    icon: Swords,
    title: '实时对战',
    desc: '与全球玩家实时较量，即时战术调整',
  },
  {
    icon: Shield,
    title: '战术布置',
    desc: '深度战术系统，临场指挥调度',
  },
  {
    icon: Users,
    title: '转会市场',
    desc: '发掘新星，打造梦幻阵容',
  },
]

export default function Home() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const [isScrolled, setIsScrolled] = useState(false)
  const heroRef = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start']
  })

  const heroOpacity = useTransform(scrollYProgress, [0, 1], [1, 0])
  const heroScale = useTransform(scrollYProgress, [0, 1], [1, 1.05])

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 50)
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const handleStartGame = () => {
    if (isAuthenticated) {
      navigate('/dashboard')
    } else {
      navigate('/login')
    }
  }

  return (
    <div className="min-h-screen bg-[#0A0A0F] text-[#E2E2F0] overflow-x-hidden font-sans">
      {/* 导航栏 */}
      <motion.header
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          isScrolled 
            ? 'bg-[#0A0A0F]/90 backdrop-blur-xl border-b border-[#0D4A4D]' 
            : 'bg-transparent'
        }`}
      >
        <div className="max-w-[1440px] mx-auto px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2.5 group">
              <img 
                src="/logo.png" 
                alt="闪电超级联赛"
                className="w-9 h-9 rounded-lg object-cover shadow-[0_0_20px_rgba(13,115,119,0.4)] group-hover:shadow-[0_0_30px_rgba(13,115,119,0.6)] transition-shadow duration-300"
              />
              <span className="text-lg font-semibold tracking-tight">
                闪电超级联赛
              </span>
            </Link>

            {/* 右侧 */}
            <button
              onClick={handleStartGame}
              className="px-5 py-2 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-sm font-medium rounded-lg transition-colors shadow-[0_4px_12px_rgba(13,115,119,0.35)]"
            >
              进入游戏
            </button>
          </div>
        </div>
      </motion.header>

      {/* Hero Section */}
      <section ref={heroRef} className="relative h-screen flex items-center justify-center overflow-hidden">
        {/* 背景 */}
        <motion.div 
          style={{ opacity: heroOpacity, scale: heroScale }}
          className="absolute inset-0 z-0"
        >
          <div 
            className="absolute inset-0 bg-cover bg-center bg-no-repeat"
            style={{
              backgroundImage: `url('https://images.unsplash.com/photo-1577223625816-7546f13df25d?w=1920&q=80')`,
            }}
          />
          {/* 深色渐变遮罩 */}
          <div className="absolute inset-0 bg-gradient-to-b from-[#0A0A0F]/80 via-[#0A0A0F]/50 to-[#0A0A0F]" />
          <div className="absolute inset-0 bg-[#0A0A0F]/40" />
          {/* 青色光晕 */}
          <div className="absolute bottom-0 left-0 right-0 h-2/3 bg-gradient-to-t from-[#0D4A4D]/20 to-transparent" />
        </motion.div>

        {/* Hero 内容 */}
        <div className="relative z-10 max-w-[1440px] mx-auto px-6 lg:px-8 text-center">
          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            className="space-y-8"
          >
            {/* 主标题 */}
            <motion.h1
              variants={fadeInUp}
              transition={fadeInUpTransition}
              className="text-5xl sm:text-6xl lg:text-8xl font-bold tracking-tight leading-[1.1]"
            >
              <span className="text-white">闪电</span>
              <span className="text-[#0D7377]">超级</span>
              <span className="text-white">联赛</span>
            </motion.h1>

            {/* 副标题 */}
            <motion.p
              variants={fadeInUp}
              transition={fadeInUpTransition}
              className="text-lg sm:text-xl text-[#8B8BA7] max-w-lg mx-auto"
            >
              打造你的足球帝国，征服绿茵场
            </motion.p>

            {/* CTA 按钮 */}
            <motion.div
              variants={fadeInUp}
              transition={fadeInUpTransition}
              className="pt-4"
            >
              <button
                onClick={handleStartGame}
                className="inline-flex items-center gap-2 px-8 py-3.5 bg-[#0D7377] hover:bg-[#0A5A5D] text-white font-medium rounded-lg transition-all duration-200 shadow-[0_4px_20px_rgba(13,115,119,0.4)] hover:shadow-[0_8px_30px_rgba(13,115,119,0.5)] hover:-translate-y-0.5"
              >
                立即开始
                <Zap className="w-4 h-4" />
              </button>
            </motion.div>

            {/* 数据概览 */}
            <motion.div
              variants={fadeIn}
              transition={fadeInTransition}
              className="flex items-center justify-center gap-8 sm:gap-12 pt-12 text-sm"
            >
              {[
                { value: '2M+', label: '经理在线' },
                { value: '150+', label: '国家地区' },
                { value: '24/7', label: '实时对战' },
              ].map((stat) => (
                <div key={stat.label} className="text-center">
                  <div className="text-2xl sm:text-3xl font-bold text-white font-mono tracking-tight">
                    {stat.value}
                  </div>
                  <div className="text-[#4B4B6A] mt-1">{stat.label}</div>
                </div>
              ))}
            </motion.div>
          </motion.div>
        </div>

        {/* 底部渐变 */}
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#0A0A0F] to-transparent z-10" />
      </section>

      {/* 核心玩法 */}
      <section className="relative py-24 lg:py-32">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3">
              核心玩法
            </h2>
            <p className="text-[#8B8BA7]">体验最真实的足球经理人生涯</p>
          </motion.div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="group"
              >
                <div className="h-full p-6 rounded-xl bg-[#12121A] border border-[#2D2D44] hover:border-[#0D7377]/50 transition-all duration-250 hover:-translate-y-1 hover:shadow-[0_12px_24px_rgba(0,0,0,0.4)]">
                  <div className="w-11 h-11 rounded-lg bg-[#0D4A4D]/40 border border-[#0D7377]/30 flex items-center justify-center mb-4">
                    <feature.icon className="w-5 h-5 text-white" />
                  </div>
                  <h3 className="text-base font-semibold text-white mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-[#8B8BA7] leading-relaxed">
                    {feature.desc}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative py-24">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="relative overflow-hidden rounded-2xl"
          >
            {/* 背景 */}
            <div className="absolute inset-0 bg-[#12121A]" />
            <div 
              className="absolute inset-0 opacity-40"
              style={{
                backgroundImage: `url('https://images.unsplash.com/photo-1551958219-acbc608c6377?w=1200&q=80')`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
              }}
            />
            <div className="absolute inset-0 bg-gradient-to-r from-[#0A0A0F] via-[#0A0A0F]/90 to-transparent" />
            {/* 青色光晕 */}
            <div className="absolute right-0 top-0 bottom-0 w-1/2 bg-gradient-to-l from-[#0D7377]/25 to-transparent" />
            
            {/* 内容 */}
            <div className="relative py-16 px-8 lg:px-16">
              <div className="max-w-xl">
                <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
                  准备好开始了吗？
                </h2>
                <p className="text-[#8B8BA7] mb-8">
                  立即加入，免费开启你的足球经理生涯。无需下载，即开即玩。
                </p>
                <button
                  onClick={handleStartGame}
                  className="inline-flex items-center gap-2 px-6 py-3 bg-[#0D7377] hover:bg-[#0A5A5D] text-white font-medium rounded-lg transition-all duration-200 shadow-[0_4px_16px_rgba(13,115,119,0.4)]"
                >
                  免费开始游戏
                  <Zap className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#0D4A4D] py-8">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            {/* Logo */}
            <div className="flex items-center gap-2">
              <img 
                src="/logo.png" 
                alt="闪电超级联赛"
                className="w-7 h-7 rounded-md object-cover"
              />
              <span className="text-sm font-medium">闪电超级联赛</span>
            </div>
            
            {/* Copyright */}
            <p className="text-sm text-[#4B4B6A]">
              © 2024 Lightning Super League
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
