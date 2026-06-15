/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    fontFamily: {
      sans: ['Inter', 'Roboto', 'system-ui', 'sans-serif'],
    },
    extend: {
      colors: {
        brand: {
          primary: '#1E3A8A', // Deep Blue
          secondary: '#0EA5E9', // Vibrant Cyan
        },
        slate: {
          50: '#F8FAFC', // Light Background
          100: '#F1F5F9', // Light Text / Alternate dark background
          800: '#1E293B',
          900: '#0F172A', // Dark Background
          950: '#020617',
        }
      }
    },
  },
  plugins: [],
}
