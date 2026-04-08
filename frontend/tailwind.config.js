/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#0A0A0F',
          secondary: '#12121A',
          tertiary: '#1E1E2D',
        },
        border: {
          DEFAULT: '#2D2D44',
        },
        text: {
          primary: '#E2E2F0',
          secondary: '#8B8BA7',
          muted: '#4B4B6A',
        },
        brand: {
          // 草场绿为主色调（深色）
          green: '#166534',
          'green-dark': '#14532D',
          'green-light': '#4ADE80',
          // 蓝色作为辅助
          blue: '#3B82F6',
          'blue-dark': '#2563EB',
        },
        // 功能色
        accent: {
          red: '#EF4444',
          yellow: '#FCD34D',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Noto Sans SC', 'sans-serif'],
        mono: ['Roboto Mono', 'JetBrains Mono', 'monospace'],
      },
      maxWidth: {
        'container': '1440px',
      },
      boxShadow: {
        'glow-green': '0 0 20px rgba(22, 101, 52, 0.4)',
        'glow-green-lg': '0 0 40px rgba(22, 101, 52, 0.5)',
        'card': '0 4px 6px rgba(0, 0, 0, 0.3)',
        'card-hover': '0 12px 24px rgba(0, 0, 0, 0.4)',
      },
      borderRadius: {
        'sm': '6px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
      },
      transitionDuration: {
        'fast': '150ms',
        'normal': '250ms',
        'slow': '350ms',
      },
    },
  },
  plugins: [],
}
