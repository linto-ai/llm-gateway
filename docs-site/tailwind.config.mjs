/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  darkMode: 'media',
  theme: {
    extend: {
      colors: {
        accent: '#00a086',
        'accent-dark': '#00c2a2',
        'accent-light': '#00c2a2',
        'dark-bg': '#0d1117',
        'dark-text': '#e6edf3',
        'dark-code-bg': '#161b22',
        'dark-border': '#30363d',
        'light-code-bg': '#f6f8fa',
        'light-border': '#d1d5db'
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      },
      maxWidth: {
        'container': '1200px'
      }
    }
  },
  plugins: []
};
