/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        navy: { 50: '#e7f0ff', 100: '#c5d9f7', 200: '#9bb8ed', 300: '#6e95e0', 400: '#4a78d4', 500: '#1e3a6e', 600: '#162c54', 700: '#0f1f3c', 800: '#0a1628', 900: '#050c16' },
        ocean: { 50: '#e6fcf8', 100: '#b3f5ea', 200: '#80eedc', 300: '#4de7ce', 400: '#1ae0c0', 500: '#00c9a7', 600: '#009e84', 700: '#007361', 800: '#00483e', 900: '#001d19' },
        alert: { red: '#ff4757', orange: '#ffa502', yellow: '#ffd32a', green: '#2ed573' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'ping-slow': 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
      },
    },
  },
  plugins: [],
}
