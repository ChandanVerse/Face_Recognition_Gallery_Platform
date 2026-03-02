/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0fdfb',
          100: '#e0fbf7',
          200: '#c1f7ef',
          300: '#a2f3e7',
          400: '#83efdf',
          500: '#00CCB4',
          600: '#00b89f',
          700: '#00a48a',
          800: '#009075',
          900: '#007c60',
        },
        accent: {
          50: '#fff5f3',
          100: '#ffebe7',
          200: '#ffd7cf',
          300: '#ffc3b7',
          400: '#ffaf9f',
          500: '#FF968C',
          600: '#ff8878',
          700: '#ff7a6a',
          800: '#ff6c5c',
          900: '#ff5e4e',
        },
        secondary: {
          50: '#fef5fb',
          100: '#fdebf7',
          200: '#fbd7ef',
          300: '#f9c3e7',
          400: '#f7afdf',
          500: '#EC9AE2',
          600: '#eb86da',
          700: '#e972d2',
          800: '#e75eca',
          900: '#e54ac2',
        },
      },
      fontFamily: {
        sans: ['Nunito', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}