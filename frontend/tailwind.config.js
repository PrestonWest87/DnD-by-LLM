/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0a0a0f',
        surface: '#12121a',
        surfaceHover: '#1a1a25',
        border: '#2a2a3a',
        primary: '#8b5cf6',
        primaryHover: '#7c3aed',
        secondary: '#06b6d4',
        accent: '#f59e0b',
        success: '#10b981',
        danger: '#ef4444',
        text: '#e2e8f0',
        textMuted: '#94a3b8',
      },
      fontFamily: {
        display: ['Cinzel', 'serif'],
        body: ['Inter', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 10px rgba(139, 92, 246, 0.3)' },
          '100%': { boxShadow: '0 0 20px rgba(139, 92, 246, 0.6)' },
        }
      }
    },
  },
  plugins: [],
}