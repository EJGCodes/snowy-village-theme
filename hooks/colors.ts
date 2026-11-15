import { makeColors } from './make-colors.js'

// Night palette pulled from the scene: deep sky navy for surfaces, snow-white
// text, aurora teal for accents, lamp-light amber for warnings.
export const { theme: COLORS, problems: COLOR_PROBLEMS } = makeColors({
  label: 'Aurora Village',
  only: 'dark',
  roles: {
    accent: '#2cc7a6',   // aurora teal
    success: '#5fe2bf',  // bright aurora green
    warning: '#f2bb5e',  // window and lamp light
    danger: '#e0675a',   // red cabin, warmed
    pro: '#9a8cf0',      // aurora violet
  },
  dark: {
    gray: {
      anchors: {
        'surface-0': '#081526',
        'surface-1': '#0c1c31',
        'surface-2': '#10223a',
        'surface-3': '#12253d',
        'text-primary': '#eaf2f8',
        'text-secondary': '#bccbd9',
        'text-muted': '#91a4b8',
      },
    },
  },
})
