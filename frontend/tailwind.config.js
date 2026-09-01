/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        // L&T Finance brand yellow/gold
        brand: {
          50: "#fff9e6",
          100: "#fff0bf",
          200: "#ffe085",
          300: "#ffcc47",
          400: "#ffbb1f",
          500: "#f9a825",
          600: "#e08e00",
          700: "#b06e00",
          800: "#8a5600",
          900: "#5c3900",
        },
        // Near-black used for the wordmark and primary text/nav surfaces
        ink: {
          50: "#f4f5f6",
          100: "#e3e5e8",
          200: "#c3c8cf",
          300: "#9aa1ab",
          400: "#6b7280",
          500: "#464d57",
          600: "#2f333c",
          700: "#22252c",
          800: "#17191e",
          900: "#0d0e11",
        },
        // Blue accent from the logo's diagonal swoosh
        accent: {
          50: "#e8f6fd",
          100: "#c8ebfb",
          200: "#93d7f6",
          300: "#5cc0ef",
          400: "#2ea6e0",
          500: "#1a8bc7",
          600: "#136fa1",
          700: "#0f577f",
          800: "#0c435f",
          900: "#093141",
        },
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.2s ease-out",
      },
    },
  },
  plugins: [],
};
