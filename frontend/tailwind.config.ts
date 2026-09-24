import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Udemy-style light palette (per owner request -- no dark theme).
        // brand: primary actions/links/progress only, not decoration.
        brand: {
          DEFAULT: "#5624d0",
          dark: "#4318a5",
        },
        ink: "#1c1d1f", // body text
        "ink-muted": "#6a6f73", // secondary/muted text
        surface: "#f7f9fa", // card/panel background, one step off white
        line: "#d1d7dc", // borders/dividers
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
