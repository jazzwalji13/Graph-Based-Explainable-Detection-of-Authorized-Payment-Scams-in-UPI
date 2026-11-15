/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "rgb(var(--c-bg) / <alpha-value>)",
        surface: "rgb(var(--c-surface) / <alpha-value>)",
        surface2: "rgb(var(--c-surface2) / <alpha-value>)",
        border: "rgb(var(--c-border) / <alpha-value>)",
        ink: "rgb(var(--c-ink) / <alpha-value>)",
        muted: "rgb(var(--c-muted) / <alpha-value>)",
        brand: "rgb(var(--c-brand) / <alpha-value>)",
        brandink: "rgb(var(--c-brandink) / <alpha-value>)",
        brandsoft: "rgb(var(--c-brandsoft) / <alpha-value>)",
        accent: "rgb(var(--c-accent) / <alpha-value>)",
        danger: "rgb(var(--c-danger) / <alpha-value>)",
        dangersoft: "rgb(var(--c-dangersoft) / <alpha-value>)",
        ok: "rgb(var(--c-ok) / <alpha-value>)",
        oksoft: "rgb(var(--c-oksoft) / <alpha-value>)",
        warn: "rgb(var(--c-warn) / <alpha-value>)",
        warnsoft: "rgb(var(--c-warnsoft) / <alpha-value>)",
      },
      borderRadius: { card: "1rem", xl2: "1.25rem" },
      boxShadow: {
        card: "0 1px 2px rgb(16 24 40 / 0.05), 0 4px 16px rgb(16 24 40 / 0.06)",
        pop: "0 12px 40px rgb(16 24 40 / 0.18)",
      },
      fontFamily: {
        sans: ['"Inter"', "system-ui", "-apple-system", '"Segoe UI"', "Roboto", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
