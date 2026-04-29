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
          green: '#166534',
          'green-dark': '#14532D',
          'green-light': '#4ADE80',
          blue: '#3B82F6',
          'blue-dark': '#2563EB',
        },
        accent: {
          red: '#EF4444',
          yellow: '#FCD34D',
        }
      },
      fontFamily: {
        pixel: ['"Press Start 2P"', 'cursive'],
        sans: ['Inter', 'Noto Sans SC', 'system-ui', 'sans-serif'],
        mono: ['Roboto Mono', 'JetBrains Mono', 'monospace'],
      },
      maxWidth: {
        'container': '1440px',
      },
      boxShadow: {
        'pixel': '4px 4px 0px rgba(0, 0, 0, 0.5)',
        'pixel-sm': '2px 2px 0px rgba(0, 0, 0, 0.5)',
        'pixel-lg': '6px 6px 0px rgba(0, 0, 0, 0.5)',
        'pixel-green': '4px 4px 0px #0A5A5D',
        'glow-green': '0 0 20px rgba(13, 115, 119, 0.4)',
        'glow-green-lg': '0 0 40px rgba(13, 115, 119, 0.5)',
        'card': '4px 4px 0px rgba(0, 0, 0, 0.3)',
        'card-hover': '6px 6px 0px rgba(0, 0, 0, 0.4)',
      },
      borderRadius: {
        'none': '0px',
        'sm': '0px',
        'md': '0px',
        'lg': '0px',
        'xl': '0px',
      },
      transitionDuration: {
        'fast': '100ms',
        'normal': '150ms',
        'slow': '200ms',
      },
    },
  },
  plugins: [],
}
