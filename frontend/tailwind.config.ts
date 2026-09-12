import type { Config } from "tailwindcss";

// Design tokens per CLAUDE.md -- decided against the frontend-design skill
// guide, following the PRD's explicit visual direction (navy sidebar,
// neutral surfaces, professional blue accent, status colors only where
// meaningful; no gradients/neon).
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          900: "#0B1626",
          800: "#16263B",
          700: "#1F3552",
        },
        accent: {
          DEFAULT: "#1D5FC7",
          50: "#EAF1FC",
          600: "#1D5FC7",
          700: "#164A9E",
        },
        surface: "#FFFFFF",
        canvas: "#F5F7FA",
        ink: {
          900: "#101828",
          600: "#3E4757",
          500: "#667085",
        },
        line: "#E4E7EC",
        status: {
          pass: "#1E8E5A",
          passBg: "#EAF7F0",
          review: "#B7791F",
          reviewBg: "#FCF3E3",
          fail: "#C0392B",
          failBg: "#FBEAE8",
          na: "#667085",
          naBg: "#F1F2F4",
        },
      },
      fontFamily: {
        heading: ["var(--font-heading)", "system-ui", "sans-serif"],
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px 0 rgba(16, 24, 40, 0.06), 0 1px 3px 0 rgba(16, 24, 40, 0.08)",
      },
    },
  },
  plugins: [],
};
export default config;
