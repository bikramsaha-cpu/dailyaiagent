import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        slatewash: "#eef5ff",
        mist: "#f8fbff",
        cyanflash: "#34d3ff",
        cobalt: "#2954ff",
      },
      boxShadow: {
        soft: "0 20px 60px rgba(15, 23, 42, 0.10)",
      },
      backgroundImage: {
        hero: "linear-gradient(135deg, #10204f 0%, #2d53ff 45%, #1ca7d8 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
