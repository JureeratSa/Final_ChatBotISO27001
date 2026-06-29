/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        tuh: {
          pink: '#FFF0F5',
          coral: '#FF7540',
          rose: '#FF4D80',
          purple: '#8B5CF6',
          indigo: '#321154',
          navy: '#080c20',
        }
      },
      fontFamily: {
        sans: ['Inter', 'Outfit', 'Sarabun', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
