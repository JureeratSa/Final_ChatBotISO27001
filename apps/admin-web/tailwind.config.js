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
          pink: '#F4D6FB',
          coral: '#809BFE',
          rose: '#8B5CF6',
          purple: '#A78BFA',
          indigo: '#0d1235',
          navy: '#04081c',
        }
      },
      fontFamily: {
        sans: ['Roboto', 'Inter', 'Outfit', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
