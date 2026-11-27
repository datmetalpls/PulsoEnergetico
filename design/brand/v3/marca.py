#!/usr/bin/env python3
"""Pulso Energético v2 · geometría del isotipo y rotulado a trazados.

Todo el texto visible se convierte a trazados con fontTools (Fraunces OFL).
Retícula del isotipo: lienzo de 96 u, módulo de 8 u, suelo/umbral en y = 88.
"""
from pathlib import Path
import math
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

V2 = Path(__file__).resolve().parent
FONTS_DIR = V2.parent / 'fonts'

C = {
    'petroleo': '#06323B', 'crema': '#FFF1D9', 'dorado': '#FFC04C',
    'dorado-texto': '#805000', 'ambar': '#B87708', 'verde': '#176B46', 'verde-claro': '#83D9AA', 'negro': '#000000', 'blanco': '#FFFFFF',
}

# ---------------------------------------------------------------- geometría
def rounded(points, radii):
    """Polilínea con esquinas redondeadas (cuadráticas) de radio por vértice."""
    d = [f'M{points[0][0]:.2f} {points[0][1]:.2f}']
    for i in range(1, len(points) - 1):
        (x0, y0), (x1, y1), (x2, y2) = points[i - 1], points[i], points[i + 1]
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        l1 = math.hypot(x1 - x0, y1 - y0); l2 = math.hypot(x2 - x1, y2 - y1)
        r = min(r, l1 * .45, l2 * .45)
        ax, ay = x1 + (x0 - x1) * r / l1, y1 + (y0 - y1) * r / l1
        bx, by = x1 + (x2 - x1) * r / l2, y1 + (y2 - y1) * r / l2
        d.append(f'L{ax:.2f} {ay:.2f}Q{x1:.2f} {y1:.2f} {bx:.2f} {by:.2f}')
    d.append(f'L{points[-1][0]:.2f} {points[-1][1]:.2f}')
    return ''.join(d)

BASE = 88  # suelo de la casa = umbral = línea base del texto

# «Casa que late»: suelo → pared → TECHO = cordillera que late (cumbre Ecuador →
# escalón del rayo → latido que entra en la casa → cumbre Chile) → pared → suelo.
H_PTS = [(4, 88), (19, 88), (19, 58), (6, 62), (28, 14), (41, 50), (48, 46), (52, 64), (70, 18),
         (90, 62), (77, 58), (77, 88), (92, 88)]
H_RAD = [0, 4, 3, 2.5, 3.4, 2.4, 2.4, 3.2, 3.4, 2.5, 3, 4, 0]
# Favicon (16–32 px): sin escalón del rayo, picos simétricos, trazo grueso, mismo alero.
F_PTS = [(-6, 90), (19, 90), (19, 62), (4, 66), (29, 24), (48, 62), (67, 24), (92, 66), (77, 62),
         (77, 90), (102, 90)]
F_RAD = [0, 4, 3, 3, 4, 4, 4, 3, 3, 4, 0]
SW = 7.5
SW_FAV = 12.5
GAP = 3.0
# Sol inscrito entre las dos cumbres con aire uniforme (calculado por sunfit):
# su distancia a la ladera Ecuador y a la ladera Chile es la misma = r + SW/2 + GAP.
SUN = None
SUN_FAV = None
DOOR = (48, 6.5, 73)   # centro x, radio del arco, y del ápice
DOOR_FAV = (48, 8, 73)

def _segdist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)

def sunfit(pts, sw, gap, top=3.0, tol=.04):
    """Busca el mayor sol equidistante (± tol) de los dos tramos más cercanos."""
    best = None
    for cx10 in range(300, 800):
        for cy10 in range(0, 500, 2):
            c = (cx10 / 10, cy10 / 10)
            ds = sorted(_segdist(c, pts[i], pts[i + 1]) for i in range(len(pts) - 1))
            r = ds[0] - sw / 2 - gap
            if ds[1] - ds[0] > tol or c[1] - r < top:
                continue
            if best is None or r > best[2]:
                best = (c[0], c[1], round(r, 2))
    return best

SUN = sunfit(H_PTS, SW, GAP)
SUN_FAV = sunfit(F_PTS, SW_FAV, 3.6, top=5)

_uid = [0]
def uid(p):
    _uid[0] += 1
    return f'{p}{_uid[0]}'

def door_path(cx, r, top, bottom):
    return (f'M{cx - r} {bottom}V{top + r}A{r} {r} 0 0 1 {cx + r} {top + r}V{bottom}Z')

def isotipo(x, y, size, line, sun, door=None, favicon=False, ring=None):
    """Casa con techo de cordillera que late. `door`=None usa el color del trazo."""
    pts, rad, sw = (F_PTS, F_RAD, SW_FAV) if favicon else (H_PTS, H_RAD, SW)
    cx, cy, r = SUN_FAV if favicon else SUN
    dx, dr, dtop = DOOR_FAV if favicon else DOOR
    d = rounded(pts, rad)
    s = size / 96
    out = [f'<g transform="translate({x:.2f} {y:.2f}) scale({s:.4f})">']
    if ring:
        out.append(f'<circle cx="48" cy="48" r="48" fill="{ring}"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{sun}"/>')
    out.append(f'<path d="{door_path(dx, dr, dtop, pts[1][1] + sw / 2)}" fill="{door or line}"/>')
    out.append(f'<path d="{d}" fill="none" stroke="{line}" stroke-width="{sw}" '
               'stroke-linecap="round" stroke-linejoin="round"/></g>')
    return ''.join(out)

# ---------------------------------------------------------------- rotulado
_font = TTFont(FONTS_DIR / 'Fraunces.ttf')
_sans = TTFont(FONTS_DIR / 'DMSans.ttf')
UPM = 2000
LOC = {'wght': 640, 'opsz': 144, 'SOFT': 100, 'WONK': 0}

# Kerning manual (unidades de fuente, 2000 upm) para «Pulso Energético».
KERN = {('P', 'u'): -40, ('u', 'l'): -10, ('l', 's'): -6, ('s', 'o'): -8,
        ('E', 'n'): -14, ('n', 'e'): -6, ('e', 'r'): -6, ('r', 'g'): -30,
        ('g', 'é'): -6, ('é', 't'): -18, ('t', 'i'): -12, ('i', 'c'): -6, ('c', 'o'): -6,
        ('r', 'e'): -10}
TRACK = -6  # interletrado óptico para tamaño display

def glyphset(font=None, loc=None):
    font = font or _font
    return font.getGlyphSet(location=loc or LOC), font.getBestCmap()

def word(text, x, y, size, fill, loc=None, track=TRACK, kern=KERN, tilde=None,
         font=None, raw=False):
    """Devuelve (svg, ancho). `tilde`=(color) reemplaza la tilde de la é por el rayo-pulso."""
    gs, cmap = glyphset(font, loc)
    sc = size / (font or _font)['head'].unitsPerEm
    pen = SVGPathPen(gs)
    cur = 0; prev = None; extra = []
    for ch in text:
        if prev:
            cur += (kern or {}).get((prev, ch), 0) + track
        gname = cmap[ord(ch)]
        if ch == 'é' and tilde:
            g = gs[cmap[ord('e')]]
            g.draw(TransformPen(pen, (sc, 0, 0, -sc, x + cur * sc, y)))
            bp = BoundsPen(gs); g.draw(bp)
            xmin, _, xmax, ymax = bp.bounds
            extra.append(tilde_rayo(x + (cur + (xmin + xmax) / 2) * sc, y - ymax * sc, size, tilde))
            cur += g.width
        else:
            g = gs[gname]
            g.draw(TransformPen(pen, (sc, 0, 0, -sc, x + cur * sc, y)))
            cur += g.width
        prev = ch
    svg = f'<path fill="{fill}" d="{pen.getCommands()}"/>' + ''.join(extra)
    return svg, cur * sc

def tilde_rayo(cx, top, size, color):
    """Tilde dibujada: un rayo relleno inclinado como acento agudo (oficio de rótulo)."""
    u = size / 100 * 1.18
    # rayo local (y hacia abajo), alto 22 u; sube hacia la derecha como un agudo
    P = [(5.5, 0), (12, 0), (7.6, 8.4), (11.6, 8.4), (1.6, 22), (4.2, 11.6), (0.2, 11.6)]
    ox, oy = cx - 5.2 * u, top - 24.5 * u
    d = 'M' + 'L'.join(f'{ox + px * u:.2f} {oy + py * u:.2f}' for px, py in P) + 'Z'
    return (f'<path d="{d}" fill="{color}" stroke="{color}" stroke-width="{1.4 * u:.2f}" '
            'stroke-linejoin="round"/>')

def width(text, size, **kw):
    return word(text, 0, 0, size, '#000', **kw)[1]

def caps_on_arc(text, cx, cy, radius, size, fill, start_deg, font=None, loc=None,
                track=0, bottom=False):
    """Mayúsculas a trazados sobre un arco centrado en start_deg (0 = arriba)."""
    font = font or _font
    gs, cmap = glyphset(font, loc)
    sc = size / (font or _font)['head'].unitsPerEm
    adv = []
    for i, ch in enumerate(text):
        g = gs[cmap[ord(ch)]]
        adv.append(g.width + (track if i < len(text) - 1 else 0))
    total = sum(adv) * sc
    span = total / radius  # radianes
    out = []
    a = math.radians(start_deg) - (span / 2 if not bottom else -span / 2)
    for ch, w in zip(text, adv):
        g = gs[cmap[ord(ch)]]
        half = g.width * sc / 2 / radius
        mid = a + half if not bottom else a - half
        pen = SVGPathPen(gs)
        if not bottom:
            # glifo erguido, base sobre el arco, hacia fuera
            px = cx + radius * math.sin(mid); py = cy - radius * math.cos(mid)
            rot = mid
            ca, sa = math.cos(rot), math.sin(rot)
            # local: x' = (gx - w/2)*sc, y' = -gy*sc ; luego rotar y trasladar
            t = (ca * sc, sa * sc, sa * sc, -ca * sc,
                 px - ca * g.width * sc / 2, py - sa * g.width * sc / 2)
        else:
            px = cx + radius * math.sin(mid); py = cy - radius * math.cos(mid)
            rot = mid + math.pi
            ca, sa = math.cos(rot), math.sin(rot)
            t = (ca * sc, sa * sc, sa * sc, -ca * sc,
                 px - ca * g.width * sc / 2, py - sa * g.width * sc / 2)
        g.draw(TransformPen(pen, t))
        out.append(pen.getCommands())
        a = a + w * sc / radius if not bottom else a - w * sc / radius
    return f'<path fill="{fill}" d="{"".join(out)}"/>'

def svg_doc(w, h, body, title, desc='', bg=None):
    from html import escape
    bgr = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t d"><title id="t">{escape(title)}</title>'
            f'<desc id="d">{escape(desc)}</desc>{bgr}{body}</svg>')
