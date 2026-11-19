"""Generates the pixel-art snowy village scene as an animated SVG.

Run:  python tools/build_scene.py
Writes hooks/scene.ts (the SVG as a string constant) and tools/preview.html.
The art is a 384x216 pixel grid; each layer is packed into one <path> per
color, built from merged rectangles, so the SVG stays under 131,072 chars.
Layout: a tall sky, with the mountains, village and lake in the lower part.
"""
import json
import math
import os
import random

W, H = 384, 216
SHORE = 168          # rows < SHORE are land and sky; rows >= SHORE are lake
BASE = SHORE - 4     # the row cabins stand on
LIMIT = 131072
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


# ---------------------------------------------------------------- noise ----
def hash2(x, y, s):
    n = (x * 374761393 + y * 668265263 + s * 982451653) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def vnoise(x, y, s):
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi
    u = xf * xf * (3 - 2 * xf)
    v = yf * yf * (3 - 2 * yf)
    a, b = hash2(xi, yi, s), hash2(xi + 1, yi, s)
    c, d = hash2(xi, yi + 1, s), hash2(xi + 1, yi + 1, s)
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v


def fbm(x, y, s, octaves=3):
    total, amp, norm = 0.0, 1.0, 0.0
    for i in range(octaves):
        total += vnoise(x, y, s + i * 17) * amp
        norm += amp
        x, y, amp = x * 2, y * 2, amp * 0.5
    return total / norm


def ridge(points, x):
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return None


def ridge_slope(points, x):
    a, b = ridge(points, x - 1), ridge(points, x + 1)
    if a is None or b is None:
        return 0.0
    return (b - a) / 2


def pick(palette, t):
    t = min(max(t, 0.0), 0.9999)
    return palette[int(t * len(palette))]


def new_grid():
    return [[None] * W for _ in range(H)]


def put(g, x, y, col):
    if 0 <= x < W and 0 <= y < H:
        g[y][x] = col


def box(g, x0, y0, x1, y1, col):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(g, x, y, col)


# ------------------------------------------------------------------ sky ----
SKY = ['#050f22', '#06142a', '#081a35', '#0a2040', '#0d284c', '#103058',
       '#143963', '#18436d', '#1d4e77', '#235a80']
ROWDITH = [0.0, 0.5, 0.25, 0.75]


def build_sky():
    g = new_grid()
    for y in range(SHORE):
        for x in range(W):
            t = (y / SHORE) ** 1.25
            t += 0.2 * math.exp(-((x - 195) / 85) ** 2) * (y / SHORE) ** 2
            f = t * (len(SKY) - 1)
            i = int(f)
            if f - i > ROWDITH[y % 4]:
                i += 1
            g[y][x] = SKY[min(i, len(SKY) - 1)]
    return g


# --------------------------------------------------------------- aurora ----
AUR = ['#0e4262', '#10566f', '#136c7c', '#178688', '#1ca394', '#27bfa3',
       '#4fdcb9', '#93f0d2', '#d2fbea']
AUR_T = [0.13, 0.22, 0.32, 0.43, 0.55, 0.67, 0.79, 0.9, 0.99]
# Each ribbon: the line of its lower hem, its strength, a noise seed, and the
# span of x over which it fades in and out (so the ribbons don't form a grid).
RIBBONS = [
    ([(-10, 74), (80, 68), (200, 82), (310, 66), (400, 38)], 1.25, 101,
     (-200, -100, 600, 700)),
    ([(100, 58), (190, 38), (290, 30), (400, 12)], 0.8, 106, (110, 220, 600, 700)),
    ([(-10, 30), (90, 22), (200, 6)], 0.7, 111, (-200, -100, 90, 190)),
]


def smooth(points, x):
    """Like ridge(), but eased between the points, so the line has no corners."""
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return y0 + (y1 - y0) * (1 - math.cos(math.pi * t)) / 2
    return None


def ramp(x, a, b):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def aurora_intensity(x, y):
    i = 0.0
    for pts, amp, seed, (in0, in1, out0, out1) in RIBBONS:
        hem = smooth(pts, x)
        if hem is None:
            continue
        hem = hem * 1.12 + 3
        hem += 3 * (vnoise(x / 9, 0, seed) - 0.5)
        d = y - hem
        reach = 12 + 30 * vnoise(x / 6.5, 0, seed + 1) ** 1.4    # how tall this ray is
        rays = math.exp(-d / 2.6) if d > 0 else math.exp(d / reach)
        halo = math.exp(-d / 7) if d > 0 else math.exp(d / 52)   # soft light around it
        bright = 0.55 + 0.45 * vnoise(x / 38, 0, seed + 2)        # slow change along it
        w = ramp(x, in0, in1) * (1 - ramp(x, out0, out1))
        i += amp * w * bright * (0.72 * rays + 0.3 * halo)
    # a low, wide glow on the horizon behind the mountains
    i += 0.3 * math.exp(-(((x - 205) / 120) ** 2 + ((y - (SHORE - 28)) / 22) ** 2))
    # faint light between the ribbons, so no patch of dark sky is boxed in
    i += 0.1 * math.exp(-(((x - 215) / 95) ** 2 + ((y - 68) / 42) ** 2))
    return i


def build_aurora():
    g = new_grid()
    for y in range(SHORE):
        for x in range(W):
            v = aurora_intensity(x, y)
            lvl = -1
            for k, th in enumerate(AUR_T):
                if v >= th:
                    lvl = k
            if lvl >= 0:
                g[y][x] = AUR[lvl]
    return g


# ---------------------------------------------------------------- stars ----
def build_stars(aurora):
    rnd = random.Random(11)
    groups = {k: [] for k in ('s', 't1', 't2', 't3')}
    for _ in range(430):
        x, y = rnd.randrange(W), rnd.randrange(0, SHORE - 30)
        if aurora[y][x] in AUR[4:]:
            continue
        col = rnd.choice(['#ffffff', '#ffffff', '#dfe9ff', '#bcd2f5', '#9fb6dd',
                          '#ffe9c4', '#6f8fc0', '#6f8fc0'])
        groups[rnd.choice(['s', 's', 's', 't1', 't2', 't3'])].append((x, y, col))
    bright = [(62, 14), (286, 40), (348, 86), (22, 44), (246, 10), (144, 8),
              (330, 22), (98, 62), (10, 96), (372, 58)]
    return groups, bright


# ------------------------------------------------------------ mountains ----
def tr(points, k):
    return [(round(x * 1.2), SHORE - (100 - y) * k) for x, y in points]


FAR = tr([(134, 100), (140, 88), (145, 79), (149, 73), (152, 70), (155, 72),
          (158, 75), (162, 77), (166, 80), (170, 78), (175, 74), (180, 71),
          (182, 69), (186, 72), (190, 77), (195, 83), (202, 92), (210, 100)], 1.95)
LEFT = tr([(0, 42), (4, 38), (8, 39), (12, 36), (16, 37), (20, 32), (23, 30),
           (26, 27), (29, 26), (32, 23), (34, 25), (37, 26), (40, 29), (44, 30),
           (48, 34), (52, 37), (56, 41), (60, 43), (65, 48), (70, 49), (73, 46),
           (76, 45), (80, 47), (86, 50), (90, 50), (94, 53), (99, 54), (103, 56),
           (108, 55), (113, 56), (117, 55), (121, 57), (127, 59), (133, 65),
           (139, 72), (145, 80), (151, 88), (157, 94), (163, 100)], 1.02)
RIGHT = tr([(176, 100), (181, 93), (187, 85), (194, 75), (198, 70), (201, 66),
            (204, 61), (207, 57), (210, 55), (213, 52), (217, 51), (221, 49),
            (225, 49), (229, 47), (234, 46), (239, 44), (244, 44), (249, 42),
            (253, 40), (257, 40), (261, 38), (265, 37), (269, 37), (273, 35),
            (278, 34), (282, 33), (287, 33), (292, 32), (298, 33), (303, 32),
            (308, 33), (313, 33), (320, 35)], 0.96)

HAZE_PAL = ['#163a5c', '#1c4669', '#27557a', '#3d6f93']
FAR_PAL = ['#2f4c66', '#3f607c', '#577b98', '#7799b5', '#a8c6db', '#d4e8f3']
ROCK_PAL = ['#0d1622', '#162231', '#213143', '#30455b']
SNOW_PAL = ['#3d566f', '#587490', '#7f9bb6', '#a6bdd3', '#c6d8e7', '#e6f0f7']
FAR_ROCK = ['#22364b', '#2d445a', '#3b566d', '#4c6a82']
GRAY_PAL = ['#0f151e', '#19222e', '#26313f', '#354353', '#475667', '#5b6a7b']
DUST_PAL = ['#6c7d93', '#93a4b8', '#b7c5d4', '#d5dfe9']


def facet(x, y, points, spurs):
    """Light from the upper left: lit to the left of a spur line, shaded to its right."""
    f = 0.0
    for sx, k in spurs:
        sy = ridge(points, sx)
        if sy is None or y < sy:
            continue
        dx = x - (sx + (y - sy) * k)
        band = 3 + (y - sy) * 0.4
        if 0 <= dx < band:
            f = min(f, -(1 - dx / band))
        elif -band < dx < 0 and f >= 0:
            f = max(f, (1 + dx / band) * 0.8)
    return f


def build_mountains():
    g = new_grid()
    # hazy range far behind everything
    for x in range(W):
        top = SHORE - 38 - 24 * fbm(x / 46, 0, 51, 3) - 5 * abs(math.sin(x / 9.5))
        for y in range(int(top), SHORE):
            depth = y - top
            cap = depth < 3 + 3 * vnoise(x / 4, y / 3, 52)
            v = (0.75 if cap else 0.3) + (vnoise(x / 10, y / 8, 53) - 0.5) * 0.3
            g[y][x] = pick(HAZE_PAL, v)
    # far center peaks: gray rock showing through the snow, a little hazy
    far_spurs = [(183, 0.55), (218, 0.5), (201, 0.3), (170, 0.4), (232, 0.6)]
    for x in range(W):
        top = ridge(FAR, x)
        if top is None:
            continue
        sl = ridge_slope(FAR, x)
        for y in range(int(math.ceil(top)), SHORE):
            depth = y - top
            f = facet(x, y, FAR, far_spurs)
            streak = fbm(x / 3 + y / 6, y / 7 - x / 22, 61)
            rock = streak > 0.5 - depth * 0.006 + f * 0.12
            light = 0.62 + f * 0.34 - sl * 0.14 + (fbm(x / 6, y / 6, 3) - 0.5) * 0.34
            light -= max(0, depth - 16) * 0.02
            if rock:
                g[y][x] = pick(FAR_ROCK, light)
            else:
                g[y][x] = pick(SNOW_PAL[1:], light)
            if depth < 1.2:
                g[y][x] = SNOW_PAL[5] if sl < 0.4 else SNOW_PAL[3]
    # left massif
    left_spurs = [(38, 0.5), (14, 0.7), (26, 0.25), (58, 0.6), (90, 0.5),
                  (108, 0.75), (130, 0.6), (146, 0.8), (74, 0.2)]
    for x in range(W):
        top = ridge(LEFT, x)
        if top is None:
            continue
        sl = ridge_slope(LEFT, x)
        for y in range(int(math.ceil(top)), SHORE):
            depth = y - top
            f = facet(x, y, LEFT, left_spurs)
            streak = fbm(x / 3.6 + y / 7, y / 9 - x / 26, 21)
            rock = streak > 0.6 - depth * 0.004 + f * 0.1
            light = 0.6 + f * 0.36 - sl * 0.12 + (fbm(x / 8, y / 8, 4) - 0.5) * 0.36
            light -= max(0, depth - 34) * 0.01
            light -= max(0, y - (SHORE - 18)) * 0.03
            if rock:
                g[y][x] = pick(ROCK_PAL, light * 0.9)
            else:
                g[y][x] = pick(SNOW_PAL, light)
            if depth < 1.3:
                g[y][x] = SNOW_PAL[5] if sl < 0.4 else SNOW_PAL[3]
    # a lone bright snow pixel with dark rock on all four sides reads as a stray
    # light, so it takes the rock's color
    for y in range(1, SHORE - 1):
        for x in range(1, W - 1):
            if ridge(LEFT, x) is None or g[y][x] not in SNOW_PAL[4:]:
                continue
            around = [g[y][x - 1], g[y][x + 1], g[y - 1][x], g[y + 1][x]]
            if all(c in ROCK_PAL for c in around):
                g[y][x] = max(set(around), key=around.count)
    # hand touch-ups: two bright pixels poking up from a snow patch into dark rock
    for x, y in ((20, 119), (25, 119)):
        if g[y][x] == SNOW_PAL[5] and g[y - 1][x] in ROCK_PAL:
            g[y][x] = g[y - 1][x]
    # and a small too-bright patch above them, shaped like a sideways T, toned
    # down to the snow just left of it
    for x, y in ((20, 112), (20, 113), (21, 113), (20, 114)):
        if g[y][x] == SNOW_PAL[5]:
            g[y][x] = SNOW_PAL[4]
    # and the patch of gray rock between it and the snow below, filled with
    # snow: the softer shade up top and along the left, the brighter shade
    # where it meets the bright snow below
    for y in range(114, 120):
        for x in range(20, 25):
            if g[y][x] == ROCK_PAL[3]:
                g[y][x] = SNOW_PAL[4] if x == 20 or y <= 116 else SNOW_PAL[5]
    # right mountain: mostly gray rock, with snow on the top and in streaks
    right_spurs = [(258, 0.5), (276, 0.3), (300, 0.45), (330, 0.35), (356, 0.5),
                   (244, 0.2), (228, 0.35), (316, 0.6)]
    for x in range(W):
        top = ridge(RIGHT, x)
        if top is None:
            continue
        sl = ridge_slope(RIGHT, x)
        for y in range(int(math.ceil(top)), SHORE):
            depth = y - top
            f = facet(x, y, RIGHT, right_spurs)
            n = fbm(x / 6, y / 4, 31)
            streak = fbm(x / 3.4 - y / 7, y / 9 + x / 28, 35)
            # snow lies thick near the ridge and thins out down the face
            cover = 0.62 - depth * 0.011 + f * 0.1 + (n - 0.5) * 0.3
            snow = streak < cover
            light = 0.55 + f * 0.36 + sl * 0.1 + (fbm(x / 8, y / 8, 33) - 0.5) * 0.36
            light -= max(0, depth - 30) * 0.008
            light -= max(0, y - (SHORE - 16)) * 0.03
            if snow:
                g[y][x] = pick(SNOW_PAL, light)
            else:
                g[y][x] = pick(GRAY_PAL, light * 0.95)
            if depth < 1.3:
                g[y][x] = SNOW_PAL[5] if sl > -0.4 else SNOW_PAL[3]
    # hand touch-up: a small L of snow on the rock above the last cabin,
    # filled with the rock around it
    for x, y in ((364, 126), (364, 127), (364, 128), (365, 128)):
        if g[y][x] in SNOW_PAL:
            g[y][x] = GRAY_PAL[4]
    return g


# ------------------------------------------------------ treeline + ground --
PINE = ['#07141a', '#0c1f25', '#12303a']
PINE_SNOW = ['#8aa6bf', '#cfe0ee']
GROUND = ['#16263a', '#213549', '#30485f', '#476380', '#6584a0', '#8ba6c0']
ROCKC = '#0b131c'


def ground_top(x):
    return SHORE - 9 + int(round((fbm(x / 22, 0, 41, 2) - 0.5) * 5))


def build_treeline():
    """A band of small dark pines hiding the feet of the mountains."""
    g = new_grid()
    rnd = random.Random(8)
    for row, (count, hmin, hmax, col) in enumerate([(120, 5, 10, PINE[0]), (90, 4, 8, PINE[1])]):
        for _ in range(count):
            cx = rnd.randrange(-2, W + 2)
            if 150 < cx < 236 and rnd.random() < 0.75:
                continue          # keep the gap to the far peaks open
            h = rnd.randint(hmin, hmax)
            base = ground_top(min(max(cx, 0), W - 1)) + 1 - row
            for k in range(h):
                half = (k + 1) // 2 if k % 3 else k // 2
                for xx in range(cx - half, cx + half + 1):
                    put(g, xx, base - h + k, col)
            if rnd.random() < 0.4:
                put(g, cx, base - h, PINE_SNOW[0])
                put(g, cx - 1, base - h + 2, PINE_SNOW[0])
    return g


def build_ground():
    g = new_grid()
    for x in range(W):
        top = ground_top(x)
        for y in range(top, SHORE):
            d = y - top
            v = 0.62 - d * 0.045 + (fbm(x / 7, y / 2.5, 43) - 0.5) * 0.5
            if d == 0:
                v += 0.22
            if y >= SHORE - 2:
                v = 0.1 + (vnoise(x / 3, y, 44) - 0.5) * 0.2
            g[y][x] = pick(GROUND, v)
    rnd = random.Random(4)
    for _ in range(26):                       # shore rocks
        x = rnd.randrange(W - 4)
        w = rnd.randint(2, 4)
        box(g, x, SHORE - 2, x + w, SHORE - 1, ROCKC)
        box(g, x + 1, SHORE - 3, x + w - 1, SHORE - 3, ROCKC)
        put(g, x + 1, SHORE - 3, '#2b3d50')
    return g


def pine(g, cx, base, h):
    """A foreground pine with snow on its boughs."""
    box(g, cx, base - 1, cx, base, '#24160d')
    top = base - 2 - h
    for k in range(h):
        tier = k % 4
        half = 1 + tier + k // 4 if k else 0
        half = min(half, 1 + h // 3)
        y = top + k + 1
        for xx in range(cx - half, cx + half + 1):
            put(g, xx, y, PINE[2] if xx <= cx else PINE[1])
        if tier == 3 or k == h - 1:
            put(g, cx - half, y, PINE_SNOW[1])
            put(g, cx - half + 1, y, PINE_SNOW[0])
        if tier == 1 and half > 1:
            put(g, cx - 1, y, PINE_SNOW[0])
    put(g, cx, top, PINE_SNOW[1])
    put(g, cx, top + 1, PINE_SNOW[1])


# -------------------------------------------------------------- village ----
LOG = ['#5a381f', '#7a4e2b', '#3a2414']       # log shade, log light, gap
LOG_END = ['#93663c', '#2a1a10']
EAVE = '#22150c'
SNOW = ['#eef4fa', '#b4c8dd', '#8aa4bf']
STONE = ['#646b78', '#474d59']
WIN_BASE = '#a8672a'
WIN = '#ffd772'
WIN_BAR = '#d9963f'
LAMP = '#fff4cf'
GLOW = '#f2bb5e'
SPILL = ['#b39566', '#7f7a6c']

# x0, width, wall height, kind, window offsets, door offset (or None), chimney offset
CABINS = [
    # by the docks, left and right
    (20, 15, 8, 'gable', [9], 3, 10),
    (262, 19, 8, 'side', [3, 12], 9, 13),
    (290, 15, 9, 'gable', [2], 9, 10),
    (340, 13, 7, 'gable', [7], 2, 3),
    # the front row of the village, with room between the cabins
    (98, 15, 8, 'gable', [8], 2, 3),
    (120, 19, 8, 'side', [2, 12], 8, 4),
    (147, 13, 9, 'gable', [7], 2, 8),
    (168, 17, 8, 'side', [2, 10], 7, 12),
    (193, 15, 9, 'gable', [2], 9, 10),
    (216, 19, 8, 'side', [3, 12], 9, 4),
    (242, 13, 8, 'gable', [7], 2, 3),
]
LAMPS = [44, 86, 116, 164, 212, 238, 258, 314]
PINES = [(8, 12), (14, 9), (42, 14), (52, 8), (70, 11), (80, 8), (90, 11),
         (258, 11), (310, 14), (322, 9), (334, 12), (360, 15), (370, 10), (378, 13)]

# The village behind the front row climbs a hill in rows. The buildings stay
# the same size, but each row back has less detail: the nearest is fully
# drawn, the next is dimmed, and the ones behind are dark shapes with a few
# lit windows. Each row: (lift above the shore row, width range, wall height,
# first x, last x, detail from 3 = full down to 0 = bare silhouette).
ROWS = [
    (27, (9, 12), 5, 96, 266, 0),
    (23, (9, 13), 5, 84, 280, 0),
    (18, (10, 13), 6, 88, 274, 1),
    (13, (10, 13), 6, 78, 284, 2),
    (8, (10, 13), 7, 84, 262, 3),
]
SHADOW = ['#0d1727', '#132033', '#1b2c43']        # far, mid, near silhouettes
SHADOW_SNOW = ['#3a5673', '#486684', '#5a7a99']    # their roofs, catching a little light
WALLS = [('#4b3020', '#3a2416'), ('#5a3a24', '#9d9080'), ('#8f8678', '#7a7266'),
         ('#6a3a2a', '#55301f'), ('#55402c', '#b0a591'), ('#3f2a1c', '#33221a')]
DARK_WIN = '#1c1512'


def mix(c, t, to='#101c2e'):
    t = min(max(t, 0.0), 1.0)
    ch = lambda h, k: int(h[1 + 2 * k:3 + 2 * k], 16)
    return '#' + ''.join(f'{int(round(ch(c, k) + (ch(to, k) - ch(c, k)) * t)):02x}' for k in range(3))


def hill(x):
    """How far the valley floor has risen at a column: 0 at the docks, 1 across the middle."""
    return ramp(x, 64, 122) * (1 - ramp(x, 234, 298))


WIN_BASES = {WIN_BASE}      # every color a window pane is drawn in, lit or not


def stamp(g, fx, rnd, detail, x0, x1, y0, y1, draw, wall=None):
    """Draw one building on its own, then lay it in the scene with as much
    detail as its row keeps. Its lights are only proposed here: build_village
    keeps them if the building is still mostly in view once all is drawn.
    wall is (first x, last x, y) of plain wall, where a silhouette may be lit."""
    t, tf = new_grid(), {'win': []}
    draw(t, tf)
    snow, cells, lights = set(SNOW), {}, []
    for y in range(max(0, y0), min(H, y1 + 1)):
        for x in range(max(0, x0), min(W, x1 + 1)):
            c = t[y][x]
            if c is None:
                continue
            if detail == 3:
                g[y][x] = c
            elif detail == 2:                         # dimmed, detail still readable
                g[y][x] = mix(c, 0.5, SHADOW_SNOW[2] if c in snow else SHADOW[2])
            else:                                     # a dark shape with a paler roof
                g[y][x] = SHADOW_SNOW[detail] if c in snow else SHADOW[detail]
            cells[(x, y)] = g[y][x]
    if detail >= 2:                                   # the building's own windows
        for x, y, c in tf['win']:
            if rnd.random() < (1.0 if detail == 3 else 0.75):
                lights.append((x, y, mix(WIN_BASE, 0.25 * (3 - detail), SHADOW[0]),
                               mix(c, 0.14 * (3 - detail), '#b87a3a')))
            elif (x, y) in cells:
                g[y][x] = cells[(x, y)] = mix(DARK_WIN, 0.5, SHADOW[2])
    elif wall is not None and wall[1] >= wall[0]:     # a silhouette: at most one light, in its wall
        for x in rnd.sample(range(wall[0], wall[1] + 1),
                            min(wall[1] - wall[0] + 1, rnd.choice([0, 1, 1, 1]))):
            lights.append((x, wall[2], mix(WIN_BASE, 0.6, SHADOW[0]),
                           mix(WIN, 0.4 - 0.12 * detail, '#b87a3a')))
    fx['houses'].append((detail, cells, lights))


def chalet(g, fx, rnd, x0, base, w, wall_h):
    x1, top = x0 + w - 1, base - wall_h + 1
    upper, lower = rnd.choice(WALLS)
    half = top + wall_h // 2
    box(g, x0, top, x1, half, upper)
    box(g, x0, half + 1, x1, base, lower)
    box(g, x1, top, x1, base, '#241710')
    if wall_h >= 6:                                   # a balcony under the upper floor
        box(g, x0, half, x1, half, '#2a1a10')
    if rnd.random() < 0.6:                            # gable end facing us
        r = 0
        while True:
            y = top - 1 - r
            left, right = x0 - 1 + 2 * r, x1 + 1 - 2 * r
            if left > right:
                break
            box(g, left, y, right, y, upper)
            box(g, left, y, min(left + 1, right), y, SNOW[0])
            box(g, max(right - 1, left), y, right, y, SNOW[1])
            r += 1
        put(g, x0 + w // 2, top - r, SNOW[0])
        if w >= 9:
            put(g, x0 + w // 2, top - 2, WIN_BASE)
            if rnd.random() < 0.6:
                fx['win'].append((x0 + w // 2, top - 2, WIN))
    else:                                             # eaves facing us: a slab of snow
        box(g, x0 - 1, top - 1, x1 + 1, top - 1, SNOW[2])
        box(g, x0 - 1, top - 2, x1 + 1, top - 2, SNOW[0])
        box(g, x0, top - 3, x1 - 1, top - 3, SNOW[0])
        put(g, x1 + 1, top - 2, SNOW[1])
        if rnd.random() < 0.5:
            cx = x0 + rnd.randint(1, w - 3)
            box(g, cx, top - 5, cx + 1, top - 3, STONE[0])
            box(g, cx, top - 6, cx + 1, top - 6, SNOW[0])
    floors = [top + 1] + ([half + 2] if wall_h >= 6 else [])
    for wy in floors:
        for wx in range(x0 + 1, x1 - 1, 3):
            tall = wall_h >= 5 and wy + 1 <= base - 1
            lit = rnd.random() < 0.72
            for yy in ([wy, wy + 1] if tall else [wy]):
                put(g, wx, yy, WIN_BASE if lit else DARK_WIN)
                if lit:
                    fx['win'].append((wx, yy, WIN if rnd.random() < 0.8 else '#ffbf5a'))


def church(g, fx, x0, base):
    """A stone church: nave with a snowy roof, tower and a pointed spire."""
    stone, shade, slate = '#8d8a86', '#5f5d5c', '#1f2a36'
    box(g, x0 + 6, base - 6, x0 + 19, base, stone)
    box(g, x0 + 19, base - 6, x0 + 19, base, shade)
    box(g, x0 + 5, base - 7, x0 + 20, base - 7, SNOW[2])
    box(g, x0 + 5, base - 8, x0 + 20, base - 8, SNOW[0])
    box(g, x0 + 6, base - 9, x0 + 19, base - 9, SNOW[0])
    for wx in range(x0 + 8, x0 + 18, 3):              # tall arched windows
        box(g, wx, base - 4, wx, base - 2, WIN_BASE)
        for yy in range(base - 4, base - 1):
            fx['win'].append((wx, yy, WIN))
    box(g, x0, base - 17, x0 + 5, base, stone)        # tower
    box(g, x0 + 5, base - 17, x0 + 5, base, shade)
    box(g, x0 + 2, base - 15, x0 + 3, base - 13, WIN_BASE)
    for xx in (x0 + 2, x0 + 3):
        for yy in range(base - 15, base - 12):
            fx['win'].append((xx, yy, '#ffe9a8'))
    box(g, x0 + 2, base - 9, x0 + 3, base - 8, DARK_WIN)
    box(g, x0 - 1, base - 18, x0 + 6, base - 18, SNOW[0])
    for r in range(8):                                # spire
        left = x0 + (r + 1) // 3
        right = x0 + 5 - (r + 1) // 3
        if left > right:
            left = right = x0 + 2
        box(g, left, base - 19 - r, right, base - 19 - r, slate)
        put(g, left, base - 19 - r, SNOW[1])
    box(g, x0 + 2, base - 28, x0 + 3, base - 27, slate)
    box(g, x0 + 2, base - 31, x0 + 2, base - 29, '#d9c58a')   # cross
    put(g, x0 + 1, base - 30, '#d9c58a')
    put(g, x0 + 3, base - 30, '#d9c58a')


def small_pine(g, cx, base, h):
    for k in range(h):
        half = (k + 1) // 2
        box(g, cx - half, base - h + k + 1, cx + half, base - h + k + 1, PINE[1])
    put(g, cx, base - h, SNOW[1])
    put(g, cx - 1, base - h + 2, SNOW[2])


def build_hillside(g, fx):
    rnd = random.Random(21)
    for x in range(60, 302):                          # the snowy valley floor, rising gently
        hl = hill(x)
        if hl <= 0:
            continue
        top = BASE - int(round(30 * hl + 5 * hl * (fbm(x / 16, 0, 71, 2) - 0.5)))
        for y in range(top, BASE + 1):
            v = 0.45 + (fbm(x / 7, y / 3, 72, 2) - 0.5) * 0.6 + (0.15 if y == top else 0)
            g[y][x] = mix(pick(GROUND[1:5], v), 0.18 + min(0.22, (BASE - y) / 110), '#1d3048')
    for lift, (wmin, wmax), wall_h, xa, xb, detail in ROWS:      # far rows first
        x = xa + rnd.randint(0, 6)
        while x < xb:
            w = rnd.randint(wmin, wmax)
            hl = hill(x + w // 2)
            base = BASE - int(round(lift * hl)) + rnd.choice([-1, 0, 0, 1])
            if hl < (0.4 if detail <= 1 else 0.15):   # far rows keep to the middle of the valley
                x += w
                continue
            if rnd.random() < 0.32:                   # open ground, sometimes with a pine
                gap = rnd.randint(5, 13)
                if rnd.random() < 0.65:
                    cx, h = x + gap // 2, rnd.randint(5, 8)
                    stamp(g, fx, rnd, detail, cx - 5, cx + 5, base - h - 1, base,
                          lambda t, tf: small_pine(t, cx, base, h))
                x += gap
                continue
            if detail == 2 and 160 <= x < 176:
                stamp(g, fx, rnd, detail, x - 2, x + 22, base - 34, base,
                      lambda t, tf: church(t, tf, x, base))
                x += 24
                continue
            stamp(g, fx, rnd, detail, x - 3, x + w + 3, base - wall_h - 9, base,
                  lambda t, tf: chalet(t, tf, rnd, x, base, w, wall_h),
                  wall=(x + 2, x + w - 3, base - wall_h // 2))
            x += w + rnd.randint(1, 5)


def cabin(g, fx, x0, w, wall_h, kind, wins, door, chim):
    x1, base = x0 + w - 1, BASE
    top = base - wall_h + 1
    for y in range(top, base + 1):
        col = LOG[(base - y) % 3]
        box(g, x0, y, x1, y, col)
        end = LOG_END[0] if (base - y) % 3 == 1 else LOG_END[1]
        put(g, x0, y, end)
        put(g, x1, y, end)
        if (base - y) % 3 == 1:               # notched log ends stick out
            put(g, x0 - 1, y, LOG[0])
            put(g, x1 + 1, y, LOG[0])
    box(g, x0 - 1, base + 1, x1 + 1, base + 1, SNOW[1])       # drift at the foot
    put(g, x0 - 2, base + 1, SNOW[2])
    put(g, x1 + 2, base + 1, SNOW[2])
    if kind == 'side':
        box(g, x0 - 2, top - 1, x1 + 2, top - 1, EAVE)
        box(g, x0 - 2, top - 2, x1 + 2, top - 2, SNOW[1])
        box(g, x0 - 2, top - 3, x1 + 2, top - 3, SNOW[0])
        box(g, x0 - 1, top - 4, x1 + 1, top - 4, SNOW[0])
        box(g, x0 + 1, top - 5, x1 - 2, top - 5, SNOW[0])
        put(g, x1 + 2, top - 3, SNOW[1])
        for ix in range(x0 - 1, x1 + 2, 4):   # icicles
            put(g, ix, top, '#cfe3f5')
        roof_y = top - 5
    else:
        r = 0
        while True:
            y = top - 1 - r
            left, right = x0 - 2 + 2 * r, x1 + 2 - 2 * r
            if left > right:
                break
            box(g, left, y, right, y, LOG[(base - y) % 3])
            box(g, left, y, min(left + 2, right), y, SNOW[0])
            box(g, max(right - 2, left), y, right, y, SNOW[1])
            if right - left > 6:
                put(g, left + 3, y, EAVE)
                put(g, right - 3, y, EAVE)
            r += 1
        roof_y = top - r
        box(g, x0 + w // 2 - 1, roof_y, x0 + w // 2 + 1, roof_y, SNOW[0])
        if w >= 15:                           # small attic window
            put(g, x0 + w // 2, top - 2, WIN_BASE)
            fx['win'].append((x0 + w // 2, top - 2, WIN))
    # chimney with a snow cap
    cx = x0 + chim
    cy = (top - 5 if kind == 'side' else top - 3 - min(chim, w - 1 - chim) // 2)
    box(g, cx, cy - 3, cx + 2, cy, STONE[0])
    box(g, cx + 2, cy - 3, cx + 2, cy, STONE[1])
    put(g, cx, cy - 1, STONE[1])
    box(g, cx - 1, cy - 4, cx + 3, cy - 4, SNOW[0])
    fx['smoke'].append((cx + 1, cy - 6))
    # door
    if door is not None:
        dx = x0 + door
        box(g, dx, base - 5, dx + 3, base, '#2a1a10')
        box(g, dx + 1, base - 4, dx + 2, base, '#4a2f19')
        box(g, dx, base + 1, dx + 3, base + 1, SNOW[0])
    # four-pane windows with warm light spilling on the snow
    for off in wins:
        wx, wy = x0 + off, top + 1
        box(g, wx, wy, wx + 4, wy + 4, '#22150c')
        box(g, wx + 1, wy + 1, wx + 3, wy + 3, WIN_BASE)
        box(g, wx - 1, wy + 5, wx + 5, wy + 5, LOG_END[0])    # sill
        put(g, wx, wy + 5, SNOW[0])
        put(g, wx + 1, wy + 5, SNOW[0])
        for px in range(3):
            for py in range(3):
                bar = px == 1 or py == 1
                fx['win'].append((wx + 1 + px, wy + 1 + py, WIN_BAR if bar else WIN))
        for sx in range(wx - 1, wx + 6):
            fx['spill'].append((sx, base + 2, SPILL[0]))
        for sx in range(wx, wx + 5):
            fx['spill'].append((sx, base + 3, SPILL[1]))


def build_village():
    g = new_grid()
    fx = {'win': [], 'smoke': [], 'spill': [], 'glow': [], 'lamp': [], 'houses': []}
    build_hillside(g, fx)
    for x in range(W):                                # a snow floor along the shore
        n = vnoise(x / 4, 0, 81)
        put(g, x, BASE + 1, SNOW[0] if n > 0.35 else SNOW[1])
        put(g, x, BASE + 2, SNOW[1] if n > 0.55 else SNOW[2])
    for cx, h in PINES:
        pine(g, cx, BASE + 1, h)
    # fences by the docks
    for xa, xb in [(38, 60), (308, 336)]:
        box(g, xa, BASE - 1, xb, BASE - 1, '#3a2414')
        for px in range(xa, xb + 1, 4):
            box(g, px, BASE - 3, px, BASE, '#4a2f19')
            put(g, px, BASE - 4, SNOW[0])
    for spec in CABINS:
        cabin(g, fx, *spec)
    post, pane = '#161016', '#b9742c'
    for lx in LAMPS:
        box(g, lx, BASE - 5, lx, BASE, post)                     # the post
        box(g, lx - 1, BASE - 6, lx + 1, BASE - 6, post)         # lantern floor
        box(g, lx - 1, BASE - 7, lx + 1, BASE - 7, pane)         # glass, lit from inside
        box(g, lx - 1, BASE - 8, lx + 1, BASE - 8, post)         # cap
        put(g, lx, BASE - 9, post)                               # finial
        box(g, lx - 1, BASE + 1, lx + 1, BASE + 1, SNOW[1])
        ly = BASE - 7
        fx['lamp'].append((lx, ly, LAMP))
        for dx in (-1, 1):
            fx['glow'].append((lx + dx, ly, GLOW))
        for sx in range(lx - 3, lx + 4):
            fx['spill'].append((sx, BASE + 2, SPILL[0] if abs(sx - lx) < 2 else SPILL[1]))
    # snow piled in the gaps between neighbouring shore cabins: low, so a lamp
    # post or whatever stands behind still shows above it
    spans = sorted((x0, x0 + w - 1) for x0, w, *_ in CABINS)
    for (_, left), (right, _) in zip(spans, spans[1:]):
        a, b = left + 2, right - 2
        if not 2 <= b - a <= 14:
            continue
        for k, y in enumerate(range(BASE, BASE - 4, -1)):
            xa, xb = a + (k + 1) // 2, b - k // 2 - (k > 0)
            if xa > xb:
                break
            box(g, xa, y, xb, y, SNOW[0])
            put(g, xb, y, SNOW[2])
            if xb - xa >= 2:
                put(g, xb - 1, y, SNOW[1])
    # the shore cabins' own windows: drop any that something now covers
    fx['win'] = [(x, y, c) for x, y, c in fx['win'] if g[y][x] == WIN_BASE]
    # Lights of the houses behind: only for a building still mostly in view, and
    # only where the lit pixel itself is not covered. A silhouette's light must
    # also still have its own wall above and below it.
    dark = set(SHADOW)
    for detail, cells, lights in fx.pop('houses'):
        seen = sum(1 for (x, y), c in cells.items() if g[y][x] == c)
        if not cells or seen / len(cells) < 0.45:
            continue
        for x, y, base_col, lit_col in lights:
            if g[y][x] != cells.get((x, y)):
                continue
            if detail <= 1 and not (g[y - 1][x] in dark and g[y + 1][x] in dark):
                continue
            g[y][x] = base_col
            fx['win'].append((x, y, lit_col))
    lit = {(x, y) for x, y, _ in fx['win']}
    keep = []
    for x, y, c in fx['win']:
        if any((x + dx, y + dy) in lit for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            keep.append((x, y, c))
        else:                                         # a lone lit pixel: make it a dark pane
            g[y][x] = DARK_WIN
    fx['win'] = keep
    return g, fx


# --------------------------------------------------------------- encode ----
def rects_of(grid, y_max=H):
    """Merge identical runs on consecutive rows into rectangles."""
    open_runs, rects = {}, []
    for y in range(y_max + 1):
        runs = set()
        if y < y_max:
            row = grid[y]
            x = 0
            while x < W:
                c = row[x]
                if c is None:
                    x += 1
                    continue
                x0 = x
                while x < W and row[x] == c:
                    x += 1
                runs.add((x0, x, c))
        nxt = {}
        for key, y0 in open_runs.items():
            if key in runs:
                nxt[key] = y0
            else:
                rects.append((key[0], y0, key[1] - key[0], y - y0, key[2]))
        for key in runs:
            if key not in nxt:
                nxt[key] = y
        open_runs = nxt
    return rects


def paths(rects):
    """Per color: rows one pixel high become strokes (shorter to write), taller
    blocks become filled rectangles. Each is placed relative to the one before."""
    by = {}
    for x, y, w, h, c in rects:
        by.setdefault(c, []).append((y, x, w, h))
    fills, lines = [], []
    for c, items in by.items():
        items.sort()
        for flat in (False, True):
            d, px, py = [], 0, 0
            for y, x, w, h in items:
                if (h == 1) != flat:
                    continue
                if not d:
                    d.append(f'M{x} {y}')
                else:
                    dx, dy = x - px, y - py
                    d.append(f'm{dx}{dy}' if dy < 0 else f'm{dx} {dy}')
                if flat:
                    d.append(f'h{w}')
                    px, py = x + w, y
                else:
                    d.append(f'h{w}v{h}h-{w}')
                    px, py = x, y + h
            if d and flat:
                lines.append(f'<path stroke="{c}" d="{"".join(d)}"/>')
            elif d:
                fills.append(f'<path fill="{c}" d="{"".join(d)}"/>')
    out = ''.join(fills)
    if lines:
        out += '<g fill="none" transform="translate(0 .5)">' + ''.join(lines) + '</g>'
    return out


def encode(grid, y_max=H):
    return paths(rects_of(grid, y_max))


def anim(attr, values, dur, begin=0.0, times=None, discrete=True):
    """A SMIL animation. No CSS: the desktop app runs none inside a scene."""
    kind = 'animate attributeName="opacity"' if attr == 'opacity' else \
        'animateTransform attributeName="transform" type="translate"'
    out = f'<{kind} values="{values}" dur="{dur}s" repeatCount="indefinite"'
    if discrete:
        out += ' calcMode="discrete"'
    if times:
        out += f' keyTimes="{times}"'
    if begin:
        out += f' begin="-{begin:g}s"'
    return out + '/>'


def glide(values, dur, begin=0.0):
    """A smooth translate through `values` ("x y;x y;..."), easing in and out of
    each one, instead of jumping a whole pixel at a time."""
    n = len(values.split(';'))
    times = ';'.join(f'{k / (n - 1):.4f}'.rstrip('0').rstrip('.') or '0' for k in range(n))
    splines = ';'.join(['.45 0 .55 1'] * (n - 1))
    out = (f'<animateTransform attributeName="transform" type="translate" values="{values}" '
           f'dur="{dur}s" repeatCount="indefinite" calcMode="spline" keyTimes="{times}" keySplines="{splines}"')
    if begin:
        out += f' begin="-{begin:g}s"'
    return out + '/>'


def dots(points, attrs='', inner=''):
    seen, rects = set(), []
    for x, y, c in points:
        if (x, y) not in seen and 0 <= x < W and 0 <= y < H:
            seen.add((x, y))
            rects.append((x, y, 1, 1, c))
    return f'<g{attrs}>{paths(rects)}{inner}</g>'


TWINKLE = '1;.6;.25;.6'
FLICKER = ('1;.6;1;.85', '0;.5;.55;.8')


def diagnostic():
    """Four test squares at the top center, to see which kinds of animation the
    desktop app lets through. Each starts red. Build with SCENE_DIAG=1."""
    x, y, n = 154, 72, 16
    sq = lambda i: f'x="{x + i * (n + 4)}" y="{y}" width="{n}" height="{n}"'
    return (
        f'<rect x="{x - 4}" y="{y - 4}" width="{4 * (n + 4) + 4}" height="{n + 8}" fill="#000"/>'
        # 1: turns green if SVG animation tags survive at all
        f'<rect {sq(0)} fill="#e22"><set attributeName="fill" to="#2e2" begin="0s"/></rect>'
        # 2: blinks green/blue if SVG animation tags run over time
        f'<rect {sq(1)} fill="#e22"><animate attributeName="fill" values="#2e2;#22e" dur="1s" '
        'calcMode="discrete" repeatCount="indefinite"/></rect>'
        # 3: turns green if a <style> block is applied
        '<style>.dg{fill:#2e2}@keyframes dk{from{fill:#2e2}to{fill:#22e}}'
        '.da{animation:dk 1s steps(1,jump-none) infinite alternate}</style>'
        f'<rect {sq(2)} fill="#e22" class="dg"/>'
        # 4: blinks green/blue if CSS animations run
        f'<rect {sq(3)} fill="#e22" class="da"/>'
    )


def clawd(x0, yb):
    """Mini Clawd sitting in the boat in a light green beanie. x0 is its left
    edge (arms included), yb the bottom row of its body. Its legs reach down
    behind the hull, out of sight.
    It blinks, and waves now and then as the boat drifts along."""
    body, dark = '#d97757', '#2b1a14'
    beanie, brim, pom = '#b6f0c2', '#7fd49a', '#f0fff2'
    r = [(x0 + 1, yb - 3, 8, 4, body),                # body
         (x0, yb - 1, 1, 1, body),                    # left arm, resting
         (x0 + 2, yb - 2, 1, 1, dark), (x0 + 7, yb - 2, 1, 1, dark),      # eyes
         (x0 + 1, yb - 4, 8, 1, brim),                # beanie brim
         (x0 + 2, yb - 5, 6, 1, beanie), (x0 + 3, yb - 6, 4, 1, beanie),
         (x0 + 4, yb - 7, 2, 1, pom)]
    r += [(x0 + lx, yb + 1, 1, 2, body) for lx in (1, 3, 6, 8)]      # legs
    g = new_grid()
    for x, y, w, h, c in r:
        box(g, x, y, x + w - 1, y + h - 1, c)
    blink = (f'<path opacity="0" fill="{body}" d="M{x0 + 2} {yb - 2}h1v1h-1zM{x0 + 7} {yb - 2}h1v1h-1z">'
             + anim('opacity', '0;1;0', 4.6, 0, '0;.94;.98') + '</path>')
    # Waves at uneven moments of a 78 s loop, each lasting 2 s. The arm goes up
    # and stays raised for the whole wave; only the hand swings side to side.
    total, wave, swings = 78.0, 2.0, 5
    f = lambda sec: f'{sec / total:.4f}'.rstrip('0').rstrip('.')
    shown = {'down': [(0, 1)], 'up': [(0, 0)], 'out': [(0, 0)], 'in': [(0, 0)]}
    for t0 in (7, 23, 34, 52, 67):
        shown['down'] += [(t0, 0), (t0 + wave, 1)]
        shown['up'] += [(t0, 1), (t0 + wave, 0)]
        step = wave / swings
        for k in range(swings):                       # hand out, in, out, in, out
            t = t0 + k * step
            shown['out' if k % 2 == 0 else 'in'] += [(t, 1), (t + step, 0)]

    def arm(d, key, start):
        keys = shown[key]
        return (f'<path opacity="{start}" fill="{body}" d="{d}">'
                + anim('opacity', ';'.join(str(v) for _, v in keys), total, 0,
                       ';'.join(f(t) for t, _ in keys)) + '</path>')

    arms = (arm(f'M{x0 + 9} {yb - 1}h1v1h-1z', 'down', 1)          # arm resting
            # the raised arm: one pixel at the shoulder, held for the whole wave;
            # nothing is drawn below it, where the resting arm was
            + arm(f'M{x0 + 9} {yb - 2}h1v1h-1z', 'up', 0)
            + arm(f'M{x0 + 10} {yb - 3}h1v1h-1z', 'out', 0)        # hand tipped up and out
            + arm(f'M{x0 + 10} {yb - 2}h1v1h-1z', 'in', 0))        # hand straight out to the side
    return '<g>' + encode(g) + blink + arms + '</g>'


def boat(x0=214, y0=SHORE + 4):
    """A wooden rowboat, side on: planked hull and an oar. y0 is the gunwale row."""
    r = []                                    # (x, y, w, h, color)
    wood = ['#8a5c38', '#6b4226', '#55341c', '#3d2614', '#2a1a10']
    # reflection first, so the hull sits on top of it
    shade = [(x0 + 3, y0 + 5, 22, 1), (x0 + 4, y0 + 6, 20, 1), (x0 + 6, y0 + 7, 15, 1),
             (x0 + 9, y0 + 8, 8, 1)]
    out = '<g opacity=".55">' + paths([(x, y, w, h, '#040a11') for x, y, w, h in shade]) + '</g>'
    # hull: four planks narrowing to the keel, with the ends swept up
    r += [(x0 + 1, y0 + 1, 26, 1, wood[1]), (x0 + 2, y0 + 2, 24, 1, wood[2]),
          (x0 + 3, y0 + 3, 22, 1, wood[1]), (x0 + 5, y0 + 4, 18, 1, wood[3])]
    r += [(x0, y0, 28, 1, wood[0])]                                   # gunwale
    r += [(x0, y0 - 1, 2, 1, wood[0]), (x0 + 26, y0 - 1, 2, 1, wood[0]),
          (x0 + 27, y0 - 2, 1, 1, wood[0]), (x0, y0 - 2, 1, 1, wood[1])]
    r += [(x0 + 4, y0, 1, 1, '#b98a58'), (x0 + 12, y0, 1, 1, '#b98a58'),
          (x0 + 20, y0, 1, 1, '#b98a58')]                             # gunwale highlights
    for rx in (x0 + 7, x0 + 14, x0 + 21):                             # ribs across the planks
        r += [(rx, y0 + 1, 1, 3, wood[3])]
    r += [(x0 + 2, y0 + 2, 1, 1, wood[4]), (x0 + 25, y0 + 2, 1, 1, wood[4]),
          (x0 + 3, y0 + 3, 2, 1, wood[4]), (x0 + 23, y0 + 3, 2, 1, wood[4])]
    # an oar laid across the boat, blade trailing in the water
    for k in range(9):
        r += [(x0 + 3 + k, y0 - 4 + (k + 1) // 2, 1, 1, '#c9a06a')]
    r += [(x0 + 2, y0 - 5, 1, 1, '#c9a06a'), (x0 + 12, y0 + 1, 2, 1, '#a87446'),
          (x0 + 13, y0 + 2, 2, 2, '#a87446')]
    g = new_grid()                            # paint in order, so later parts overlap earlier
    for x, y, w, h, c in r:
        box(g, x, y, x + w - 1, y + h - 1, c)
    out += clawd(x0 + 12, y0 - 1) + encode(g)    # Clawd first: the hull hides its legs
    return out


def snow():
    """Light snowfall over the whole scene: three thin layers of flakes falling
    at different speeds, each swaying a little from side to side. Every layer
    is drawn twice, one screen apart, so the fall loops without a seam."""
    rnd = random.Random(44)
    out = ''
    for count, color, opacity, fall, sway in ((34, '#ffffff', '.85', 19, 5.5),
                                              (40, '#d6e4f2', '.6', 27, 7.5),
                                              (44, '#a9bfd6', '.45', 38, 9.5)):
        flakes = []
        for _ in range(count):
            x, y = rnd.randrange(W), rnd.randrange(H)
            flakes += [(x, y, 1, 1, color), (x, y - H, 1, 1, color)]
        out += (f'<g opacity="{opacity}"><g>{paths(flakes)}'
                + anim('move', f'0 0;0 {H}', fall, round(rnd.uniform(0, fall), 1), discrete=False)
                + '</g>'
                + anim('move', '0 0;3 0;0 0;-3 0;0 0', sway, discrete=False)
                + '</g>')
    return out


def window_lights(points):
    """The windows' light: steady, no flicker."""
    return dots(points)


def lamp_glows(points):
    """The lamp posts' glow: steady, no flicker."""
    return dots(points, ' opacity=".45"')


# ---------------------------------------------------------------- build ----
def build(report=False):
    sky = build_sky()
    aur = build_aurora()
    stars, bright = build_stars(aur)
    mtn = build_mountains()
    trees = build_treeline()
    ground = build_ground()
    village, fx = build_village()

    # drop pixels that a nearer, opaque layer hides: they would only cost size
    def cull(layer, covers, reach=0):
        for y in range(SHORE):
            for x in range(W):
                if layer[y][x] is not None and all(
                        any(c[yy][x] is not None for c in covers)
                        for yy in range(max(0, y - reach), y + 1)):
                    layer[y][x] = None
    cull(ground, [village])
    cull(trees, [ground, village])
    cull(mtn, [trees, ground, village])
    cull(aur, [mtn, trees, ground, village], reach=3)   # the aurora moves up to 3 rows

    star_svg = dots(stars['s'])
    for k, dur, begin in (('t1', 3.1, 0), ('t2', 4.7, 1.3), ('t3', 6.3, 2.9)):
        star_svg += dots(stars[k], inner=anim('opacity', TWINKLE, dur, begin))
    bs = []
    for x, y in bright:
        bs += [(x, y, '#ffffff'), (x - 1, y, '#8fb0e0'), (x + 1, y, '#8fb0e0'),
               (x, y - 1, '#8fb0e0'), (x, y + 1, '#8fb0e0')]
    star_svg += dots(bs, inner=anim('opacity', TWINKLE, 5.5, 0.8))
    # A shooting star every 45 s: it enters past the right edge near the top and
    # takes 12 s to cross the whole sky, leaving past the left edge. A bright
    # round comet with a soft glow.
    cycle, flight = 45, 12
    t0 = f'{1 - flight / cycle:.4f}'
    # drawn near the grid's corner (it starts off-screen, past the grid's edge)
    # and moved to its starting point, just past the right edge of the sky
    # a small round comet: a bright core in a soft circular glow, no tail
    star = new_grid()
    hx, hy = 4, 10
    for dx, dy in [(-1, -2), (0, -2), (1, -2), (-2, -1), (2, -1), (-2, 0), (2, 0),
                   (-2, 1), (2, 1), (-1, 2), (0, 2), (1, 2)]:
        put(star, hx + dx, hy + dy, '#3f6a96')         # outer glow ring
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        put(star, hx + dx, hy + dy, '#8fbce6')         # inner glow
    for dx, dy in [(0, -1), (-1, 0), (1, 0), (0, 1)]:
        put(star, hx + dx, hy + dy, '#dff0ff')
    put(star, hx, hy, '#ffffff')                       # the core
    shoot = ('<g opacity="0"><g transform="translate(388 -2)">' + encode(star) + '</g>'
             + anim('opacity', '0;0;1;1;0', cycle, 20, f'0;{t0};{float(t0) + 0.01:.4f};.985;1', discrete=False)
             + anim('move', '0 0;0 0;-440 108', cycle, 20, f'0;{t0};1', discrete=False)
             + '</g>')

    rise = ';'.join(f'{k} {2 - 2 * k}' for k in range(8))
    fade = '0;.75;.7;.6;.45;.3;.2;.1'
    smoke = ''
    smoke_rnd = random.Random(17)
    for sx, sy in fx['smoke']:
        dur = round(smoke_rnd.uniform(5.8, 9.4), 1)  # each chimney its own speed
        start = smoke_rnd.uniform(0, dur)               # and its own starting point
        for p in range(2):
            begin = round((start + p * dur / 2) % dur, 1)
            smoke += (f'<path opacity="0" fill="#9db0c6" d="M{sx} {sy}h2v2h-2zM{sx + 1} {sy - 1}h2v1h-2z">'
                      + anim('opacity', fade, dur, begin) + anim('move', rise, dur, begin) + '</path>')

    # the aurora: vertical strips that rise and fall one after another, so a
    # wave runs along the curtain, and the whole curtain slowly brightens and dims
    aw, aurora_svg = 48, ''
    for n, ax in enumerate(range(0, W, aw)):
        strip = [[c if ax <= x < ax + aw else None for x, c in enumerate(row)] for row in aur]
        aurora_svg += (
            '<g>' + encode(strip, SHORE)
            + glide('0 0;0 -3;0 0', 15, round(n * 1.9, 1))
            + '</g>')
    aurora_svg = '<g>' + aurora_svg + anim('opacity', '1;.78;1', 9, discrete=False) + '</g>'

    parts = {
        'sky': encode(sky, SHORE),
        'aurora': aurora_svg,
        'stars': star_svg,
        'mountains': encode(mtn, SHORE),
        'treeline': encode(trees, SHORE),
        'ground': encode(ground, SHORE),
        'village': encode(village, SHORE),
        'fx': dots(fx['spill'], ' opacity=".6"')
              + window_lights(fx['win'])
              + lamp_glows(fx['glow'])
              + dots(fx['lamp']) + smoke,
    }
    if report:
        for k, v in parts.items():
            print(f'  {k:10s}{len(v):7d}')
    world = '<g id="w">' + ''.join(parts.values()) + '</g>'

    # lake: the world mirrored once about the shore at half height, held still
    strips = ['<g><use href="#w" transform="matrix(1 0 0 -.5 0 ' + f'{SHORE * 1.5:g})"/>'
              + '</g>']

    rnd = random.Random(3)
    ripples = []
    for _ in range(70):
        x, y = rnd.randrange(W - 10), rnd.randrange(SHORE + 3, H)
        ripples.append((x, y, rnd.randint(2, 7), 1, '#9fd8cf'))
    ice = []
    x = 0
    while x < W:
        w = rnd.randint(3, 12)
        if rnd.random() < 0.6:
            ice.append((x, SHORE, w, 1, rnd.choice(['#2c4560', '#3f5a74', '#1f3348'])))
        x += w + rnd.randint(1, 5)
    extras = (
        # a rock in the shallows
        f'<g transform="translate(-34 {SHORE - 176})">'
        '<path fill="#081018" d="M176 184h12v3h-12zM178 183h8v1h-8zM180 182h4v1h-4z"/>'
        '<path fill="#2b3d50" d="M179 183h4v1h-4zM181 182h2v1h-2z"/>'
        '<path fill="#050b12" opacity=".6" d="M177 187h10v2h-10z"/>'
        '</g>'
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%" '
        'preserveAspectRatio="xMidYMax slice" shape-rendering="crispEdges">'
        f'<defs>{world}</defs>'
        f'<rect width="{W}" height="{H}" fill="#04101f"/>'
        '<use href="#w"/>'
        + ''.join(strips)
        + f'<rect y="{SHORE}" width="{W}" height="{H - SHORE}" fill="#020c18" opacity=".4"/>'
        + paths(ice)
        # faint by default, so the lake stays calm even where nothing animates
        + f'<g opacity=".12">{paths(ripples)}'
        + '</g>'
        + extras
        # The boat crosses from past the left edge to past the right edge in about
        # 80 s, stays out of sight for about 6 s, then starts again from the left.
        + '<g>' + boat() + anim('move', '-252 0;180 0;180 0', 86, 30, '0;.93;1', discrete=False) + '</g>'
        + snow()
        + (diagnostic() if os.environ.get('SCENE_DIAG') else '')
        + '</svg>'
    )
    return svg


if __name__ == '__main__':
    svg = build(report=True)
    print('svg chars:', len(svg), 'of', LIMIT)
    with open(os.path.join(HERE, 'preview.html'), 'w', encoding='utf-8') as f:
        f.write('<!doctype html><html><body style="margin:0;height:100vh;overflow:hidden;background:#000">'
                + svg + '</body></html>')
    if len(svg) > LIMIT:
        raise SystemExit('too big for a scene: scene.ts left as it was')
    with open(os.path.join(ROOT, 'hooks', 'scene.ts'), 'w', encoding='utf-8') as f:
        f.write('// Generated by tools/build_scene.py. Edit that script, not this file.\n')
        f.write('export const SCENE = ' + json.dumps(svg) + '\n')
