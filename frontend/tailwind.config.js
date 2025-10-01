/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./src/lightweight/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // IBM Carbon inspired colors
        'gray-10': '#f4f4f4',
        'gray-20': '#e0e0e0',
        'gray-30': '#c6c6c6',
        'gray-40': '#a8a8a8',
        'gray-50': '#8d8d8d',
        'gray-60': '#6f6f6f',
        'gray-70': '#525252',
        'gray-80': '#393939',
        'gray-90': '#262626',
        'gray-100': '#161616',
        'blue-60': '#0f62fe',
        'blue-70': '#0043ce',
        'blue-80': '#002d9c',
        'green-50': '#24a148',
        'red-50': '#da1e28',
        'yellow-30': '#f1c21b',
      },
      fontFamily: {
        'sans': ['IBM Plex Sans', 'system-ui', 'sans-serif'],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      }
    },
  },
  plugins: [],
}
