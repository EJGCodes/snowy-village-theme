import type { EngineInterface, Register, ThemeSetArgs } from 'claude-code'

import { COLORS, COLOR_PROBLEMS } from './colors'
import { SCENE } from './scene'

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
    return 'Snowy Village theme is on.'
  }

  return `Snowy Village theme could not be set: ${set.reason}`
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: COMMAND,
      description: 'Turn the Snowy Village theme on, or off with "/snowy-village off"',
      argumentHint: '[on|off]',
    })
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
    if (word !== '' && word !== 'on') {
      return { text: 'Use /snowy-village to turn the theme on, or /snowy-village off to turn it off.' }
    }
    await $.store.set(SWITCH, true)

    return { text: await apply($) }
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
        alt="Pixel-art night theme: green aurora over snowy mountains over a lakeside village, all reflected across the giant lake."
        isInteractive
      />
    )
  })
}
