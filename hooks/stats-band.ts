// The session stats band: a small pixel-art sign, drawn as an SVG. Everything
// here is plain string building, since a hooks module has no DOM.

export type Stats = {
  /** The session's model as the app names it, such as `claude-fable-5-2`. */
  model: string
  /** Replies Claude has finished. */
  turns: number
  tools: number
  /** How full the context window is, 0 to 100; undefined before the first reply. */
  contextPercent?: number
  /** How much of the 5-hour usage window is used, 0 to 100; undefined with no reading. */
  limitPercent?: number
  /** How much of the 7-day usage window is used, 0 to 100; undefined with no reading. */
  weekPercent?: number
  /** What fills the context window, largest first, and the window's size in tokens. */
  context?: { parts: ContextPart[]; maxTokens: number }
}

/** One slice of the context window: what it is, how big, and whether it is reserve. */
export type ContextPart = { name: string; tokens: number; isReserve: boolean }

// A pixel font five rows tall: each glyph is five equal rows of bits, top row
// first. Most are three wide; M and W are five wide so they read clearly.
const FONT: Record<string, string> = {
  A: '010101111101101', B: '110101110101110', C: '011100100100011', D: '110101101101110',
  E: '111100110100111', F: '111100110100100', G: '011100101101011', H: '101101111101101',
  I: '111010010010111', J: '001001001101010', K: '101101110101101', L: '100100100100111',
  M: '1000111011101011000110001', N: '110101101101101', O: '010101101101010', P: '110101110100100',
  Q: '010101101110011', R: '110101110101101', S: '011100010001110', T: '111010010010010',
  U: '101101101101111', V: '101101101101010', W: '1000110001101011101110001', X: '101101010101101',
  Y: '101101010010010', Z: '111001010100111',
  '0': '111101101101111', '1': '010110010010111', '2': '111001111100111', '3': '111001111001111',
  '4': '101101111001001', '5': '111100111001111', '6': '111100111101111', '7': '111001001001001',
  '8': '111101111101111', '9': '111101111001111',
  $: '011110111011110', '%': '101001010100101', '.': '000000000000010', ':': '000010000010000',
  '-': '000000111000000',
}

const NAVY = '#0c1c31'
const EDGE = '#2cc7a6'
const SNOW = '#eef4fa'
const SNOW_SHADE = '#b4c8dd'
const LABEL = '#8fa3b8'
const VALUE = '#eaf2f8'
const AMBER = '#f2bb5e'
const TEAL = '#5fe2bf'

/** The path data for `text` in the pixel font, its top-left pixel at (x, y). */
function glyphs(text: string, x: number, y: number): string {
  let d = ''
  let cx = x

  for (const ch of text) {
    const bits = FONT[ch]

    const wide = bits === undefined ? 3 : bits.length / 5

    if (bits !== undefined) {
      for (let row = 0; row < 5; row++) {
        for (let col = 0; col < wide; col++) {
          if (bits.charAt(row * wide + col) === '1') {
            d += `M${cx + col} ${y + row}h1v1h-1z`
          }
        }
      }
    }
    cx += wide + 1
  }

  return d
}

/** How many pixels wide `text` is in the pixel font, the gap after each glyph included. */
function textWidth(text: string): number {
  let w = 0

  for (const ch of text) {
    w += (FONT[ch]?.length ?? 15) / 5 + 1
  }

  return w
}

/** Mini Clawd in its green beanie, 10 pixels wide, its top-left at (x, y). */
function clawd(x: number, y: number): string {
  const rect = (dx: number, dy: number, w: number, h: number, fill: string): string =>
    `<path fill="${fill}" d="M${x + dx} ${y + dy}h${w}v${h}h-${w}z"/>`

  return (
    rect(4, 0, 2, 1, '#f0fff2') + // pom-pom
    rect(3, 1, 4, 1, '#b6f0c2') +
    rect(2, 2, 6, 1, '#b6f0c2') +
    rect(1, 3, 8, 1, '#7fd49a') + // brim
    rect(1, 4, 8, 4, '#d97757') + // body
    rect(0, 6, 1, 1, '#d97757') +
    rect(9, 6, 1, 1, '#d97757') + // arms
    rect(2, 5, 1, 1, '#2b1a14') +
    rect(7, 5, 1, 1, '#2b1a14') + // eyes
    rect(1, 8, 1, 1, '#d97757') +
    rect(3, 8, 1, 1, '#d97757') +
    rect(6, 8, 1, 1, '#d97757') +
    rect(8, 8, 1, 1, '#d97757') // legs
  )
}

/**
 * A model id as a short name the pixel font can draw: `claude-fable-5-2` and
 * `claude-fable-5-2-20260101` both become `FABLE 5.2`.
 */
export function modelName(model: string): string {
  const name = model
    .toLowerCase()
    .replace(/\[.*?\]/g, '') // a suffix such as [1m]
    .replace(/^claude-/, '')
    .replace(/-\d{8}$/, '') // a dated id's date
    .replace(/(\d)-(?=\d)/g, '$1.')
    .replace(/-/g, ' ')
    .toUpperCase()
    .replace(/[^A-Z0-9 .]/g, '')
    .trim()

  return name === '' ? '--' : name
}

/** The label and value pairs the band shows, in order. */
export function statPairs(stats: Stats): { label: string; value: string; color: string }[] {
  const pairs = [
    // the model's name stands alone, in the labels' gray
    { label: '', value: modelName(stats.model), color: LABEL },
    { label: 'TURNS', value: String(stats.turns), color: VALUE },
    { label: 'TOOLS', value: String(stats.tools), color: VALUE },
    {
      label: 'CONTEXT',
      value: stats.contextPercent === undefined ? '--' : `${stats.contextPercent}%`,
      color: (stats.contextPercent ?? 0) >= 80 ? AMBER : TEAL,
    },
  ]

  if (stats.limitPercent !== undefined) {
    pairs.push({
      label: '5H LIMIT',
      value: `${Math.round(stats.limitPercent)}%`,
      color: stats.limitPercent >= 80 ? AMBER : TEAL,
    })
  }

  return pairs
}

/** One plain line with the same figures, for a surface that draws no SVG. */
export function statsLine(stats: Stats): string {
  const line = statPairs(stats).map(pair => `${pair.label.toLowerCase()} ${pair.value.toLowerCase()}`.trim())

  if (stats.weekPercent !== undefined) {
    line.push(`7d limit ${Math.round(stats.weekPercent)}%`)
  }

  return line.join('  ·  ')
}

// The colors of the context bar's slices, in order.
const SLICES = ['#5fe2bf', '#f2bb5e', '#9a8cf0', '#7fb4ff', '#e0675a', '#b6f0c2', '#d97757', '#eaf2f8']
const TRACK = '#1b2e47'
const RESERVE = '#465a75'

/** A category's name from /context as one short word the pixel font can draw. */
export function shortName(name: string): string {
  const n = name.toLowerCase()
  const known: [string, string][] = [
    ['system prompt', 'SYSTEM'], ['mcp', 'MCP'], ['tool', 'TOOLS'], ['agent', 'AGENTS'],
    ['memory', 'MEMORY'], ['skill', 'SKILLS'], ['command', 'COMMANDS'], ['message', 'MESSAGES'],
  ]
  const hit = known.find(([part]) => n.includes(part))

  return hit !== undefined ? hit[1] : (n.split(/\s+/)[0] ?? '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8)
}

const box = (x: number, y: number, w: number, h: number, fill: string): string =>
  w <= 0 ? '' : `<path fill="${fill}" d="M${x} ${y}h${w}v${h}h-${w}z"/>`

/**
 * The band as an SVG: a snow-capped navy sign with Clawd at the left, the
 * figures in a pixel font, and under them a bar for the weekly usage limit and
 * a bar showing what fills the context window, with its legend.
 * `scale` is how many CSS pixels one art pixel takes.
 */
export function statsSvg(stats: Stats, scale = 3): { source: string; width: number; height: number } {
  // three rows of 5-pixel text, 5 pixels apart
  const textY = 9
  const barY = 19
  const legendY = 29
  const left = 17
  let x = left
  let labels = ''
  let body = ''

  for (const pair of statPairs(stats)) {
    labels += glyphs(pair.label, x, textY)
    x += pair.label === '' ? 0 : textWidth(pair.label) + 2
    body += `<path fill="${pair.color}" d="${glyphs(pair.value, x, textY)}"/>`
    x += textWidth(pair.value) + 6
  }
  const width = Math.max(x, 190)
  const right = width - 5

  // second row, left: the 7-day usage limit as a bar
  x = left
  body += `<path fill="${VALUE}" d="${glyphs('7D LIMIT', x, barY)}"/>`
  x += textWidth('7D LIMIT') + 2
  const weekW = 40
  const week = stats.weekPercent
  const weekColor = (week ?? 0) >= 80 ? AMBER : TEAL
  body += box(x, barY, weekW, 5, TRACK)
  if (week !== undefined) {
    body += box(x, barY, Math.max(week > 0 ? 1 : 0, Math.round((Math.min(week, 100) / 100) * weekW)), 5, weekColor)
  }
  x += weekW + 2
  const weekText = week === undefined ? '--' : `${Math.round(week)}%`
  body += `<path fill="${weekColor}" d="${glyphs(weekText, x, barY)}"/>`
  x += textWidth('100%') + 6

  // second row, right: what fills the context window, one colored slice each
  body += `<path fill="${VALUE}" d="${glyphs('USED BY', x, barY)}"/>`
  x += textWidth('USED BY') + 2
  const ctxX = x
  const ctxW = Math.max(20, right - ctxX)
  body += box(ctxX, barY, ctxW, 5, TRACK)
  let legend = ''
  let hasLegend = false

  if (stats.context !== undefined && stats.context.maxTokens > 0) {
    const used = stats.context.parts.filter(part => !part.isReserve && part.tokens > 0)
    const reserve = stats.context.parts.filter(part => part.isReserve).reduce((sum, part) => sum + part.tokens, 0)
    let sx = ctxX
    let lx = left

    used.forEach((part, i) => {
      const color = SLICES[i % SLICES.length] ?? VALUE
      const w = Math.min(ctxX + ctxW - sx, Math.max(1, Math.round((part.tokens / stats.context!.maxTokens) * ctxW)))

      body += box(sx, barY, w, 5, color)
      sx += w
      const word = shortName(part.name)

      if (word !== '' && lx + 5 + textWidth(word) <= right) {
        legend += box(lx, legendY + 1, 3, 3, color) + `<path fill="${LABEL}" d="${glyphs(word, lx + 5, legendY)}"/>`
        lx += 5 + textWidth(word) + 4
        hasLegend = true
      }
    })
    // the reserve kept free for compaction sits at the far end of the bar
    const rw = Math.min(ctxX + ctxW - sx, Math.round((reserve / stats.context.maxTokens) * ctxW))
    body += box(ctxX + ctxW - rw, barY, rw, 5, RESERVE)
  } else if (stats.contextPercent !== undefined) {
    body += box(ctxX, barY, Math.round((Math.min(stats.contextPercent, 100) / 100) * ctxW), 5, TEAL)
  }
  const height = hasLegend ? 38 : 28

  // snow lying on top of the sign: a full row, with soft bumps above it
  let bumps = ''
  for (let bx = 3; bx < width - 6; bx += 11) {
    const w = 4 + ((bx * 7) % 5)
    bumps += `M${bx} 1h${Math.min(w, width - 3 - bx)}v1h-${Math.min(w, width - 3 - bx)}z`
  }

  const source =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${Math.round(width * scale)}" ` +
    `height="${Math.round(height * scale)}" shape-rendering="crispEdges">` +
    `<path fill="${EDGE}" d="M1 4h${width - 2}v${height - 5}h-${width - 2}z"/>` +
    `<path fill="${NAVY}" d="M2 5h${width - 4}v${height - 7}h-${width - 4}z"/>` +
    `<path fill="${SNOW}" d="M0 2h${width}v2h-${width}z${bumps}"/>` +
    `<path fill="${SNOW_SHADE}" d="M1 4h${width - 2}v1h-${width - 2}z"/>` +
    // Clawd is 9 pixels tall: centered in the navy area, which runs from row 5 to the bottom edge
    clawd(4, 5 + Math.floor((height - 7 - 9) / 2)) +
    `<path fill="${LABEL}" d="${labels}"/>` +
    body +
    legend +
    '</svg>'

  return { source, width: Math.round(width * scale), height: Math.round(height * scale) }
}
