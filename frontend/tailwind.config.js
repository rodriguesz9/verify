/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        syne: ["Syne", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      colors: {
        bg: "#04080C",
        surface: "#0A1520",
        surfaceHigh: "#0F1E2E",
        border: "#132435",
        cyan: "#00D4FF",
        green: "#00FF87",
        red: "#FF3B5C",
        amber: "#FFB830",
        text: "#CDE8F0",
        muted: "#3A6070",
        dimmed: "#1A3A50",
      },
    },
  },
  plugins: [],
};
