import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17212b",
        mist: "#f4f7fb",
        cyan: "#26b9c7",
        coral: "#ff7d6d",
      },
      boxShadow: {
        soft: "0 20px 60px rgba(35, 52, 75, 0.12)",
      },
    },
  },
  plugins: [],
};

export default config;
