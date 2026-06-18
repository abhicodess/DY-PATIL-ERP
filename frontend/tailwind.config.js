/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    './index.html',
    './src/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: "rgba(255, 255, 255, 0.1)",
        input: "rgba(255, 255, 255, 0.05)",
        ring: "#a855f7",
        background: "#09090b",
        foreground: "#fafafa",
        primary: {
          DEFAULT: "#a855f7",
          foreground: "#fafafa",
        },
        secondary: {
          DEFAULT: "#27272a",
          foreground: "#fafafa",
        },
        destructive: {
          DEFAULT: "#ef4444",
          foreground: "#fafafa",
        },
        muted: {
          DEFAULT: "#27272a",
          foreground: "#a1a1aa",
        },
        accent: {
          DEFAULT: "rgba(168, 85, 247, 0.15)",
          foreground: "#c084fc",
        },
        card: {
          DEFAULT: "#18181b",
          foreground: "#fafafa",
        },
      },
    },
  },
  plugins: [],
}
