# Snowy Village

A pixel-art night theme for Claude Code in the Claude desktop and mobile apps:
a green aurora over snowy mountains, a lakeside village of log cabins, and
Clawd in a beanie in a rowboat, all mirrored in the lake. It also sets a
matching dark color palette.

The theme draws only in the Claude desktop and mobile apps. A terminal session
shows no theme.

## Install

At the prompt of a Claude Code terminal session:

```
/plugin install snowy-village --marketplace EJGCodes/snowy-village-theme
```

Answer `y` to add the marketplace, then press Enter to install it for your user.

Or from a shell:

```
claude plugin install snowy-village --marketplace EJGCodes/snowy-village-theme
```

## How to use

- `/snowy-village` turns the theme on.
- `/snowy-village off` turns the theme off and returns the app to its normal look.
- `/snowy-village stats` shows or hides a small pixel-art sign above the prompt box
  with the session's model, turns, tool calls, context use and 5-hour usage limit,
  plus bars for the weekly usage limit and what fills the context window.

The mod remembers the last choice, so the theme is on in new sessions unless it
was last turned off.

## Changing the art

The scene is generated. Edit `tools/build_scene.py` and run it with Python 3:

```
python tools/build_scene.py
```

It rewrites `hooks/scene.ts` and a `tools/preview.html` you can open in a
browser. A scene can be at most 131,072 characters; the script reports the
size and refuses to write one that is too big.

The scene is animated (the aurora waves, stars twinkle, chimneys smoke, and Clawd
sometimes waves to you). Make sure your app is updated to see it animated!