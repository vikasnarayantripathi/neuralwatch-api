/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#0066FF",
        dark: "#0A0A0F",
        card: "#12121A",
        border: "#1E1E2E",
      }
    },
  },
  plugins: [],
}
