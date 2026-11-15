import type { EngineInterface, Register, ThemeSetArgs } from 'claude-code'

import { COLORS, COLOR_PROBLEMS } from './colors'
import { SCENE } from './scene'

const LOOK: ThemeSetArgs = {
  colors: COLORS,
  backdrop: {
    scene: 'aurora-village',
    // A night-blue frost over the art, light enough to keep the scene visible.
    glass: { blur: 2, tint: "#081526", opacity: 0.15 },
  },
}

const COMMAND = 'aurora'
// Whether the theme is on, kept between sessions. Unset counts as on.
const SWITCH = 'on'

async function apply($: EngineInterface): Promise<string> {
  const unpainted = COLOR_PROBLEMS.find(line => line.startsWith("Desktop won't paint"))

  if (unpainted !== undefined) {
    $.ui.toast(unpainted)
  }
  const set = await $.theme.set(LOOK)

  return set.isDrawn ? 'Aurora Village theme is on.' : `Aurora Village theme is set, but not drawn: ${set.reason}`
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: COMMAND,
      description: 'Turn the Aurora Village theme on, or off with "/aurora off"',
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

      return { text: 'Aurora Village theme is off. Type /aurora to turn it back on.' }
    }
    if (word !== '' && word !== 'on') {
      return { text: 'Use /aurora to turn the theme on, or /aurora off to turn it off.' }
    }
    await $.store.set(SWITCH, true)

    return { text: await apply($) }
  })

  on('ui.render', { component: 'Backdrop' }, ($, e, next) => {
    if (e.surface !== 'desktop' && e.surface !== 'mobile') {
      return next(e)
    }
    if (e.props.scene !== 'aurora-village') {
      return next(e)
    }
    const { Svg } = $.ui.resolve(e)

    return (
      <Svg
        source={SCENE}
        alt="Pixel-art night: green aurora over snowy mountains and a lakeside village, mirrored in the lake"
        isInteractive
      />
    )
  })
}
