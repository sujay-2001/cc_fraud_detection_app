import { type Config } from "tailwindcss";
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          blue:  "#0B3C5D",
          teal:  "#00A6A6",
          gray: {
            50:  "#F8FAFC",
            100: "#F1F5F9",
            200: "#E2E8F0",
            800: "#1E293B"
          }
        },
        risk: {
          low:    "#00A6A6",
          medium: "#F59E0B",
          high:   "#EF4444"
        }
      },
      borderRadius: { card: "0.75rem" },
      boxShadow:    { card: "0 2px 6px 0 rgba(15,23,42,0.07)" }
    }
  },
  plugins: []
} satisfies Config;
