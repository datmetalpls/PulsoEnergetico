#!/usr/bin/env python3
"""Pulso Energético v2 · geometría del isotipo y rotulado a trazados.

Todo el texto visible se convierte a trazados con fontTools (Fraunces OFL).
Retícula del isotipo: lienzo de 96 u, módulo de 8 u, línea de umbral en y = 60.
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
    'dorado-texto': '#805000', 'ambar': '#B87708', 'negro': '#000000', 'blanco': '#FFFFFF',
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

BASE = 60  # línea de umbral / horizonte

# Dirección A · «Cordillera que late»: umbral → Q → pico Ecuador (R) → S bajo el
# umbral (el rayo) → pico Chile → umbral. Sol ecuatorial detrás.
# umbral → ladera → cumbre Ecuador → quiebre del rayo → caída bajo el umbral →
# cumbre Chile → umbral. El quiebre (43,44)→(52,38) es el escalón del rayo.
A_PTS = [(6, BASE), (16, BASE), (33, 16), (43, 45), (52, 39), (57, 75), (68, 32), (80, BASE), (90, BASE)]
A_RAD = [0, 6, 3.4, 2.4, 2.4, 3.4, 3.4, 6, 0]
# Versión favicon (16–32 px): un pico menos de detalle, trazo más grueso.
F_PTS = [(-4, 64), (12, 64), (32, 14), (43, 46), (53, 39), (58, 82), (70, 34), (84, 64), (100, 64)]
F_RAD = [0, 6, 4, 2.6, 2.6, 4, 4, 6, 0]

SUN = (54, 20, 17)  # cx, cy, r
SW = 7.5            # grosor del trazo a 96 u
SW_FAV = 12.0
GAP = 3.0           # aire entre trazo y sol (espacio negativo)

_uid = [0]
def uid(p):
    _uid[0] += 1
    return f'{p}{_uid[0]}'

def isotipo(x, y, size, line, sun, favicon=False, ring=None):
    """Isotipo A en (x, y) con lado `size`. El sol se oculta tras la cordillera."""
    pts, rad, sw = (F_PTS, F_RAD, SW_FAV) if favicon else (A_PTS, A_RAD, SW)
    d = rounded(pts, rad)
    m = uid('sol')
    cx, cy, r = SUN
    if favicon:
        cx, cy, r = 57, 23, 17
    # región sobre la cordillera: el propio trazado cerrado por arriba
    above = d + f'L{pts[-1][0]} -60L{pts[0][0]} -60Z'
    s = size / 96
    out = [f'<g transform="translate({x:.2f} {y:.2f}) scale({s:.4f})">',
           f'<defs><mask id="{m}" maskUnits="userSpaceOnUse" x="-10" y="-70" width="140" height="190">'
           f'<path d="{above}" fill="#fff"/>'
           f'<path d="{d}" fill="none" stroke="#000" stroke-width="{sw + 2 * GAP}" '
           f'stroke-linecap="round" stroke-linejoin="round"/></mask></defs>']
    if ring:
        out.append(f'<circle cx="48" cy="48" r="48" fill="{ring}"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{sun}" mask="url(#{m})"/>')
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
