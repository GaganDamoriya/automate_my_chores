import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b1016",
        surface: "#131a22",
        surface2: "#1a232d",
        line: "#26313d",
        accent: "#3ed0bd",
        hot: "#e6a54e",
        good: "#5cc98a",
      },
      fontFamily: {
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
