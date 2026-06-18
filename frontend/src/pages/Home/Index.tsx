import { useEffect, useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, useScroll, useTransform } from 'framer-motion'
import { Zap } from '../../components/ui/pixel-icons'
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
    title: '联赛征程',
    desc: '从业余联赛起步，一路征战顶级联赛',
  },
  {
    title: '实时对战',
    desc: '与全球玩家实时较量，即时战术调整',
  },
  {
    title: '战术布置',
    desc: '深度战术系统，临场指挥调度',
  },
  {
    title: '转会市场',
    desc: '发掘新星，打造梦幻阵容',
  },
]

const heroBg = '/home/hero-stadium-night-v2.png'
const ctaBg = '/home/cta-manager-bench-v2.png'

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
            ? 'bg-[#0A0A0F]/95 border-b-2 border-[#14532D]' 
            : 'bg-transparent'
        }`}
      >
        <div className="max-w-[1440px] mx-auto px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="block group">
              <img 
                src="/logo.png" 
                alt="闪电超级联赛"
                className="h-8 sm:h-10 w-auto object-contain"
              />
            </Link>

            {/* 右侧 */}
            <button
              onClick={handleStartGame}
              className="hidden sm:inline-flex px-4 py-2 bg-[#0A0A0F]/45 hover:bg-[#C6F135] text-[#E2E2F0] hover:text-[#0A0A0F] text-sm font-bold border-2 border-[#C6F135]/50 hover:border-[#14532D] transition-all duration-150 shadow-[3px_3px_0_rgba(0,0,0,0.55)] hover:-translate-x-0.5 hover:-translate-y-0.5"
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
              backgroundImage: `url('${heroBg}')`,
              filter: 'brightness(0.92) saturate(0.98)',
            }}
          />
          {/* 深色遮罩 */}
          <div className="absolute inset-0 bg-[#05060A]/25" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(198,241,53,0.10),transparent_34%),radial-gradient(circle_at_bottom,rgba(7,46,48,0.24),transparent_42%)]" />
          <div className="absolute inset-0 opacity-[0.08] bg-[linear-gradient(rgba(255,255,255,0.35)_1px,transparent_1px)] bg-[length:100%_4px]" />
          {/* 底部渐变 — 让下方衔接更自然 */}
          <div className="absolute bottom-0 left-0 right-0 h-1/2 bg-gradient-to-t from-[#0A0A0F] via-[#0A0A0F]/50 to-transparent" />
          {/* 顶部微渐变 — 避免和 header 冲突 */}
          <div className="absolute top-0 left-0 right-0 h-36 bg-gradient-to-b from-[#05060A]/78 to-transparent" />
        </motion.div>

        {/* Hero 内容 */}
        <div className="relative z-10 max-w-[1440px] mx-auto px-6 lg:px-8 text-center">
          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            className="space-y-7"
          >
            {/* 主标题 */}
            <motion.div
              variants={fadeInUp}
              transition={fadeInUpTransition}
            >
              <img
                src="/title.png"
                alt="闪电超级联赛"
                className="h-40 sm:h-60 lg:h-80 xl:h-[21rem] w-auto object-contain mx-auto drop-shadow-[0_16px_0_rgba(0,0,0,0.34)]"
              />
            </motion.div>

            <motion.p
              variants={fadeInUp}
              transition={fadeInUpTransition}
              className="mx-auto max-w-[32rem] text-sm sm:text-base text-[#C8CAD8] tracking-[0.18em] font-semibold"
            >
              像素足球经理 · 实时联赛模拟
            </motion.p>

            {/* CTA 按钮 */}
            <motion.div
              variants={fadeInUp}
              transition={fadeInUpTransition}
              className="pt-2"
            >
              <button
                onClick={handleStartGame}
                className="btn-primary inline-flex min-w-[11rem] items-center gap-2 px-8 py-3.5 text-base"
              >
                立即开始
                <Zap className="w-4 h-4" />
              </button>
            </motion.div>

            {/* 向下滚动提示 */}
            <motion.div
              variants={fadeIn}
              transition={fadeInTransition}
              className="pt-16"
            >
              <div className="animate-bounce text-[#7E83A1]">
                <svg className="w-6 h-6 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
              </div>
            </motion.div>
          </motion.div>
        </div>

        {/* 底部渐变 */}
        <div className="absolute bottom-0 left-0 right-0 h-32 z-10" />
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
            <h2 className="text-2xl sm:text-3xl font-bold font-pixel text-white mb-3">
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
                <div className="h-full p-6 bg-[#12121A] border-2 border-[#2D2D44] hover:border-[#C6F135]/50 transition-all duration-250 hover:-translate-y-1 hover:shadow-pixel">
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
      <section id="start" className="relative py-24 overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center opacity-70"
          style={{ backgroundImage: `url('${ctaBg}')` }}
        />
        <div className="absolute inset-0 bg-[#05060A]/62" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#0A0A0F] via-[#0A0A0F]/76 to-[#0A0A0F]/24" />
        <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-[#0A0A0F] to-transparent" />
        <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-[#0A0A0F] to-transparent" />

        <div className="relative max-w-[1440px] mx-auto px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="relative min-h-[26rem] flex items-center"
          >
            {/* 内容 */}
            <div className="relative py-16">
              <div className="max-w-xl">
                <h2 className="text-3xl sm:text-4xl font-bold font-pixel text-white mb-5 leading-tight">
                  准备好开始了吗？
                </h2>
                <p className="text-[#B9BBCD] mb-8 leading-relaxed">
                  进入教练席，接管阵容、训练、转会与比赛日决策。无需下载，即开即玩。
                </p>
                <button
                  onClick={handleStartGame}
                  className="btn-primary inline-flex items-center gap-2 px-6 py-3"
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
      <footer className="border-t-2 border-[#14532D] py-8">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            {/* Logo */}
            <div>
              <img 
                src="/logo.png" 
                alt="闪电超级联赛"
                className="h-8 w-auto object-contain"
              />
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
