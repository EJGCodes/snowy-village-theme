import type { EngineInterface, Register, ThemeSetArgs } from 'claude-code'

import { COLORS, COLOR_PROBLEMS } from './colors'
import { SCENE } from './scene'
import { statsLine, statsSvg } from './stats-band'
import type { ContextPart, Stats } from './stats-band'

const LOOK: ThemeSetArgs = {
  colors: COLORS,
  backdrop: {
    scene: 'snowy-village',
    // A night-blue frost over the art, light enough to keep the scene visible.
    glass: { blur: 2, tint: "#081526", opacity: 0.15 },
  },
}

const COMMAND = 'snowy-village'
// Whether the theme is on, kept between sessions. Unset counts as on.
const SWITCH = 'on'
// Whether the stats band shows above the prompt, kept between sessions. Unset counts as on.
const STATS = 'stats'
const USAGE =
  'Use /snowy-village to turn the theme on, /snowy-village off to turn it off, ' +
  'or /snowy-village stats to show or hide the session stats.'

async function apply($: EngineInterface): Promise<string> {
  const unpainted = COLOR_PROBLEMS.find(line => line.startsWith("Desktop won't paint"))

  if (unpainted !== undefined) {
    $.ui.toast(unpainted)
  }
  const set = await $.theme.set(LOOK)

  // Not drawn but with a request id means the theme stands and only waits for
  // an app window to attach, which is normal. Only a result with no request id
  // is a real failure.
  if (set.isDrawn || set.requestId !== undefined) {
    return 'Snowy Village theme is on!'
  }

  return `Snowy Village theme could not be set: ${set.reason}`
}

// Declared at the top of the file: the engine only lets `$` be handed to a
// function it can see here, not to one made inside `register`.
type Context = { parts: ContextPart[]; maxTokens: number }

/**
 * What fills the context window, largest first, as /context estimates it. The
 * `summary` estimate is worked out locally and sends no request.
 */
async function readContext($: EngineInterface): Promise<Context | undefined> {
  const { context } = await $.session.usage({ breakdown: 'summary' })
  const breakdown = context.breakdown

  if (breakdown === undefined) {
    return undefined
  }
  const parts = breakdown.categories
    .filter(row => row.kind === 'used' || row.kind === 'buffer')
    .map(row => ({ name: row.name, tokens: row.tokens, isReserve: row.kind === 'buffer' }))
    .sort((a, b) => b.tokens - a.tokens)

  return { parts, maxTokens: breakdown.rawMaxTokens }
}

async function measure(
  $: EngineInterface,
  turns: number,
  tools: number,
  context: Context | undefined,
): Promise<Stats> {
  const usage = await $.session.usage()
  const fiveHour = usage.rateLimits.find(limit => limit.kind === 'five_hour')
  const week = usage.rateLimits.find(limit => limit.kind === 'seven_day')

  return {
    model: await $.session.model(),
    turns,
    tools,
    ...(usage.context.percent !== undefined && { contextPercent: usage.context.percent }),
    ...(fiveHour !== undefined && { limitPercent: fiveHour.percentUsed }),
    ...(week !== undefined && { weekPercent: week.percentUsed }),
    ...(context !== undefined && { context }),
  }
}

export const register: Register = on => {
  // Counted since the mod loaded in this session; a reload starts them over.
  let turns = 0
  // The context breakdown is read when a turn ends, not on every redraw.
  let context: Context | undefined
  let hasContext = false
  let tools = 0
  let showsStats = true

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: COMMAND,
      description: 'Snowy Village theme: on, off, or "stats" to show or hide the session stats',
      argumentHint: '[on|off|stats]',
    })
    showsStats = (await $.store.get(STATS)) !== false
    if ((await $.store.get(SWITCH)) !== false) {
      await apply($)
    }

    return next(e)
  })

  on('command.run', { command: COMMAND }, async ($, e) => {
    const word = e.args.trim().toLowerCase()

    if (word === 'off') {
      await $.store.set(SWITCH, false)
      await $.theme.clear()

      return { text: 'Snowy Village theme is off. Type /snowy-village to turn it back on.' }
    }
    if (word === 'stats') {
      showsStats = !showsStats
      await $.store.set(STATS, showsStats)
      $.ui.invalidate('ui.render')

      return { text: showsStats ? 'Session stats are now showing above the prompt box!' : 'Session stats are now hidden.' }
    }
    if (word !== '' && word !== 'on') {
      return { text: USAGE }
    }
    await $.store.set(SWITCH, true)

    return { text: await apply($) }
  })

  // What the band counts, each change drawing it again.
  on('tool.call', ($, e, next) => {
    tools += 1
    $.ui.invalidate('ui.render')

    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    if (e.agentId === undefined) {
      turns += 1 // Claude's own replies; a subagent's turns are not counted
      context = await readContext($)
      hasContext = true
    }
    $.ui.invalidate('ui.render')

    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (!showsStats || e.props.hasSurvey) {
      return next(e)
    }
    if (!hasContext) {
      context = await readContext($)
      hasContext = true
    }
    const stats = await measure($, turns, tools, context)

    if (e.surface === 'desktop' || e.surface === 'mobile') {
      const { Box, Svg } = $.ui.resolve(e)
      // screen pixels per art pixel: 3 on desktop, 2 on a phone
      const sign = statsSvg(stats, e.surface === 'mobile' ? 2 : 3)

      // a full-width row with the sign in its middle
      return (
        <Box width="100%" flexGrow={1} justifyContent="center">
          <Svg
            source={sign.source}
            alt={`Session stats: ${statsLine(stats)}`}
            width={sign.width}
            height={sign.height}
          />
        </Box>
      )
    }
    if (e.surface === 'terminal') {
      const { Box, Text } = $.ui.resolve(e)

      return (
        <Box>
          <Text dimColor>{statsLine(stats)}</Text>
        </Box>
      )
    }

    return next(e)
  })

  on('ui.render', { component: 'Backdrop' }, ($, e, next) => {
    if (e.surface !== 'desktop' && e.surface !== 'mobile') {
      return next(e)
    }
    if (e.props.scene !== 'snowy-village') {
      return next(e)
    }
    const { Svg } = $.ui.resolve(e)

    return (
      <Svg
        source={SCENE}
        alt="Pixel-art night: green aurora over snowy mountains and a lakeside village, all mirrored across the lake."
        isInteractive
      />
    )
  })
}
