#!/usr/bin/env python3
"""Genera la marca v2 de Pulso Energético (SVG a trazados + PNG con Chrome headless).

Uso:  python3 build_v2.py            (solo escribe dentro de design/brand/v2/)
Requiere: fontTools, Pillow y Google Chrome instalado.
"""
from pathlib import Path
import math, subprocess, tempfile, shutil
from html import escape
from PIL import Image
from fontTools.pens.boundsPen import BoundsPen
import marca
from marca import (C, isotipo, word, caps_on_arc, svg_doc, rounded, glyphset, _sans,
                   A_PTS, F_PTS, SUN, SW, SW_FAV, GAP, BASE)

V2 = marca.V2
V1 = V2.parent
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
TMP = Path(tempfile.mkdtemp(prefix='pe-v2-'))

def save(name, w, h, body, title, desc='', bg=None):
    (V2 / name).write_text(svg_doc(w, h, body, title, desc, bg), encoding='utf-8')

def sans(text, x, y, size, fill, wght=500, track=0):
    return word(text, x, y, size, fill, loc={'wght': wght, 'opsz': 14}, kern={}, track=track,
                font=_sans)

def cap_height(loc=None):
    gs, cmap = glyphset(None, loc)
    bp = BoundsPen(gs); gs[cmap[ord('P')]].draw(bp)
    return bp.bounds[3] / 2000

# ------------------------------------------------------------- variantes
# (trazo, sol, tilde, texto)
VAR = {
    'color':    (C['petroleo'], C['dorado'], C['ambar'], C['petroleo']),
    'negativo': (C['crema'], C['dorado'], C['dorado'], C['crema']),
    'negro':    (C['negro'], C['negro'], C['negro'], C['negro']),
    'blanco':   (C['blanco'], C['blanco'], C['blanco'], C['blanco']),
}
DESC = {
    'color': 'Color sobre crema',
    'negativo': 'Negativo sobre petróleo',
    'negro': 'Una tinta negra',
    'blanco': 'Una tinta blanca',
}
WM = 'Pulso Energético'

def wordmark(x, y, size, variant):
    _, _, tilde, ink = VAR[variant]
    return word(WM, x, y, size, ink, tilde=tilde)

def horizontal(variant):
    line, sun, _, _ = VAR[variant]
    s = 112; ix, iy = 24, 24
    base = iy + s * BASE / 96            # la línea base del texto se apoya en el umbral
    peak = iy + s * 16 / 96
    size = (base - peak) / cap_height() * 0.98
    wm, w = wordmark(ix + s + 22, base, size, variant)
    W = math.ceil(ix + s + 22 + w + 28)
    return W, 160, isotipo(ix, iy, s, line, sun) + wm

def vertical(variant):
    line, sun, _, _ = VAR[variant]
    size = 62
    w = word(WM, 0, 0, size, '#000', tilde='#000')[1]
    W = math.ceil(w + 64); s = 176
    body = isotipo((W - s) / 2, 24, s, line, sun)
    wm, _ = wordmark((W - w) / 2, 24 + s + 58, size, variant)
    return W, 24 + s + 58 + 40, body + wm

def star4(cx, cy, r, fill):
    k = r * .28
    pts = [(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k), (cx, cy + r),
           (cx - k, cy + k), (cx - r, cy), (cx - k, cy - k)]
    return (f'<path d="M{"L".join(f"{a:.2f} {b:.2f}" for a, b in pts)}Z" fill="{fill}" '
            f'stroke="{fill}" stroke-width="{r * .12:.2f}" stroke-linejoin="round"/>')

def sello(variant):
    """Sello circular estilo Cuypleto: arco «ECUADOR × CHILE · ODS 7»."""
    W = 480; c = 240
    if variant == 'color':
        disk, ink, acc, line, sun = C['petroleo'], C['crema'], C['dorado'], C['crema'], C['dorado']
    elif variant == 'negativo':
        disk, ink, acc, line, sun = None, C['crema'], C['dorado'], C['crema'], C['dorado']
    else:
        disk = None; ink = acc = line = sun = C[variant]
    b = []
    if disk:
        b.append(f'<circle cx="{c}" cy="{c}" r="230" fill="{disk}"/>')
    b.append(f'<circle cx="{c}" cy="{c}" r="221" fill="none" stroke="{acc}" stroke-width="3"/>')
    b.append(f'<circle cx="{c}" cy="{c}" r="166" fill="none" stroke="{ink}" stroke-width="2"/>')
    # puntos de compás entre los anillos interiores: ritmo de pulso
    for i in range(72):
        a = math.radians(i * 5)
        if 60 < i * 5 < 120 or 240 < i * 5 < 300:
            continue
        rr = 159
        b.append(f'<circle cx="{c + rr * math.sin(a):.2f}" cy="{c - rr * math.cos(a):.2f}" '
                 f'r="{1.6 if i % 3 else 2.4}" fill="{acc}"/>')
    loc = {'wght': 700, 'opsz': 72, 'SOFT': 50, 'WONK': 0}
    b.append(caps_on_arc('ECUADOR × CHILE · ODS 7', c, c, 182, 34, ink, 0, loc=loc, track=150))
    b.append(caps_on_arc('PULSO ENERGÉTICO', c, c, 207, 34, ink, 180, loc=loc, track=170, bottom=True))
    b.append(star4(c - 194, c, 11, acc)); b.append(star4(c + 194, c, 11, acc))
    s = 236
    b.append(isotipo(c - s / 2, c - s / 2 - 6, s, line, sun))
    return W, W, ''.join(b)

def favicon_body(size=32):
    k = size / 96
    clip = marca.uid('fav')
    return (f'<defs><clipPath id="{clip}"><circle cx="{48 * k}" cy="{48 * k}" r="{48 * k}"/></clipPath></defs>'
            f'<circle cx="{48 * k}" cy="{48 * k}" r="{48 * k}" fill="{C["petroleo"]}"/>'
            f'<g clip-path="url(#{clip})">'
            + isotipo(0, 0, size, C['crema'], C['dorado'], favicon=True) + '</g>')

# ------------------------------------------------------------- direcciones
def iso_b(x, y, s, ink=C['petroleo'], sun=C['dorado']):
    """B · Mitad del Mundo: sol ecuatorial arriba, Cruz del Sur abajo, el ecuador late."""
    m = marca.uid('b')
    eq = rounded([(8, 50), (30, 50), (38, 28), (46, 66), (53, 50), (88, 50)], [0, 3, 3, 3, 3, 0])
    rays = ''.join(
        f'<path d="M{48 + 27 * math.cos(math.radians(a)):.2f} {50 - 27 * math.sin(math.radians(a)):.2f}'
        f'L{48 + 34 * math.cos(math.radians(a)):.2f} {50 - 34 * math.sin(math.radians(a)):.2f}" '
        f'stroke="{sun}" stroke-width="4" stroke-linecap="round"/>' for a in (18, 45, 72, 108, 135, 162))
    cross = (star4(66, 60, 4.2, ink) + star4(66, 82, 4.6, ink) + star4(57, 71, 3.6, ink)
             + star4(75, 69, 3.4, ink) + star4(70, 76, 2, ink))
    return (f'<g transform="translate({x} {y}) scale({s / 96})">'
            f'<defs><mask id="{m}" maskUnits="userSpaceOnUse" x="0" y="0" width="96" height="96">'
            f'<rect width="96" height="50" fill="#fff"/><path d="{eq}" fill="none" stroke="#000" '
            f'stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/></mask></defs>'
            f'<circle cx="48" cy="48" r="44" fill="none" stroke="{ink}" stroke-width="5"/>'
            f'<circle cx="48" cy="50" r="21" fill="{sun}" mask="url(#{m})"/>{rays}{cross}'
            f'<path d="{eq}" fill="none" stroke="{ink}" stroke-width="6" stroke-linecap="round" '
            'stroke-linejoin="round"/></g>')

def iso_c(x, y, s, ink=C['petroleo'], acc=C['dorado']):
    """C · La sede late: la casa comunitaria con el latido adentro."""
    house = rounded([(4, 80), (18, 80), (18, 46), (48, 18), (78, 46), (78, 80), (92, 80)],
                    [0, 4, 4, 5, 4, 4, 0])
    pulse = rounded([(26, 62), (36, 62), (43, 44), (52, 74), (58, 62), (70, 62)], [0, 2.5, 2.5, 2.5, 2.5, 0])
    return (f'<g transform="translate({x} {y}) scale({s / 96})">'
            f'<path d="{house}" fill="none" stroke="{ink}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{pulse}" fill="none" stroke="{acc}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></g>')

def direction(letter, title, logic, iso_svg, wm_svg, recommended=False):
    W, H = 960, 540
    b = [iso_svg, wm_svg]
    b.append(f'<path d="M64 404H896" stroke="{C["petroleo"]}" stroke-opacity=".25" stroke-width="1.5"/>')
    b.append(sans(f'DIRECCIÓN {letter}', 64, 70, 18, C['ambar'], 700, track=120)[0])
    b.append(word(title, 64, 456, 34, C['petroleo'])[0])
    b.append(sans(logic, 64, 494, 20, C['petroleo'], 450)[0])
    if recommended:
        t, w = sans('RECOMENDADA', 0, 0, 15, C['petroleo'], 700, track=120)
        b.append(f'<rect x="{896 - w - 32:.1f}" y="46" width="{w + 32:.1f}" height="34" rx="17" fill="{C["dorado"]}"/>')
        b.append(sans('RECOMENDADA', 896 - w - 16, 68.5, 15, C['petroleo'], 700, track=120)[0])
    save(f'direccion-{letter.lower()}.svg', W, H, ''.join(b), f'Pulso Energético · Dirección {letter}',
         logic, bg=C['crema'])

def directions():
    # A
    wm, w = word(WM, 352, 262, 66, C['petroleo'], tilde=C['ambar'])
    direction('A', 'Cordillera que late',
              'Un solo trazo es umbral, cumbre andina y rayo; el sol asoma entre Ecuador y Chile.',
              isotipo(64, 120, 260, C['petroleo'], C['dorado']), wm, recommended=True)
    # B
    loc = {'wght': 760, 'opsz': 144, 'SOFT': 0, 'WONK': 0}
    wm1 = word('PULSO', 380, 228, 72, C['petroleo'], loc=loc, track=60, kern={})[0]
    wm2 = word('ENERGÉTICO', 380, 290, 44, C['petroleo'], loc=loc, track=120, kern={})[0]
    kick = sans('ECUADOR × CHILE', 382, 330, 18, C['ambar'], 700, track=200)[0]
    direction('B', 'Mitad del Mundo',
              'El ecuador late entre dos cielos: el sol de la Mitad del Mundo arriba, la Cruz del Sur abajo.',
              iso_b(72, 110, 250), wm1 + wm2 + kick)
    # C
    loc = {'wght': 520, 'opsz': 144, 'SOFT': 100, 'WONK': 1}
    wm = word('pulso energético', 370, 262, 70, C['petroleo'], loc=loc, kern={('r', 'g'): -30},
              track=-8)[0]
    direction('C', 'La sede late',
              'La casa comunitaria lleva el latido adentro: la energía se cuida entre vecinos.',
              iso_c(64, 112, 260), wm)

# ------------------------------------------------------------- construcción
def construccion():
    W, H = 1000, 1080; k = 8; ox, oy = 116, 150
    P = lambda x, y: (ox + x * k, oy + y * k)
    b = []
    grid = C['petroleo']
    for i in range(0, 97, 4):
        op = .28 if i % 24 == 0 else (.14 if i % 8 == 0 else .06)
        b.append(f'<path d="M{ox + i * k} {oy}V{oy + 96 * k}M{ox} {oy + i * k}H{ox + 96 * k}" '
                 f'stroke="{grid}" stroke-opacity="{op}" stroke-width="1"/>')
    b.append(f'<rect x="{ox}" y="{oy}" width="{96 * k}" height="{96 * k}" fill="none" stroke="{grid}" stroke-opacity=".45"/>')
    b.append(isotipo(ox, oy, 96 * k, C['petroleo'], C['dorado']))
    cx, cy, r = SUN
    X, Y = P(cx, cy)
    b.append(f'<circle cx="{X}" cy="{Y}" r="{r * k}" fill="none" stroke="{C["ambar"]}" stroke-width="2" stroke-dasharray="8 6"/>')
    b.append(f'<path d="M{X - 10} {Y}H{X + 10}M{X} {Y - 10}V{Y + 10}" stroke="{C["ambar"]}" stroke-width="2"/>')
    b.append(f'<path d="M{X} {Y}L{X + r * k * .7071:.1f} {Y - r * k * .7071:.1f}" stroke="{C["ambar"]}" stroke-width="2"/>')
    yb = oy + BASE * k
    b.append(f'<path d="M{ox - 60} {yb}H{ox + 96 * k + 60}" stroke="#B42318" stroke-width="1.5" stroke-dasharray="10 6"/>')
    for (x, y) in A_PTS:
        px, py = P(x, y)
        b.append(f'<circle cx="{px}" cy="{py}" r="6" fill="{C["crema"]}" stroke="#B42318" stroke-width="2"/>')
    def lab(t, x, y, size=17, color=C['petroleo'], wght=500):
        b.append(sans(t, x, y, size, color, wght)[0])
    lab('Construcción del isotipo · Dirección A «Cordillera que late»', 64, 64, 26, wght=700)
    lab('Lienzo 96 u · módulo 8 u (líneas finas) · retícula mayor 24 u · todas las uniones y remates redondeados', 64, 98, 17)
    def leader(x1, y1, x2, y2):
        b.append(f'<path d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}" stroke="{C["petroleo"]}" stroke-width="1.2"/>')
    lab('umbral y = 60 · línea base del texto', ox + 10, yb + 34, 16, '#B42318', 600)
    lab(f'sol ecuatorial: centro ({cx}, {cy}) · r = {r} u', X + r * k * .7071 + 14, Y - r * k * .7071 - 8, 16, C['ambar'], 600)
    px, py = P(33, 16); lab('cumbre Ecuador (33, 16)', px - 230, py - 4, 15); leader(px - 52, py - 9, px - 10, py - 4)
    px, py = P(68, 32); lab('cumbre Chile (68, 32)', px + 46, py + 40, 15); leader(px + 8, py + 8, px + 42, py + 34)
    px, py = P(47.5, 42); lab('escalón del rayo', ox + 10, oy + 44 * k, 15, wght=600); leader(ox + 140, oy + 44 * k - 5, px - 28, py)
    px, py = P(57, 75); lab('latido bajo el umbral (57, 75)', px + 34, py + 26, 15); leader(px + 8, py + 8, px + 30, py + 20)
    yb2 = oy + 96 * k + 64
    lab(f'Trazo {SW} u (≈ 1/13 del lienzo) · aire entre trazo y sol {GAP} u por lado · radio de unión 2,4–6 u', 64, yb2, 17)
    lab(f'Compensación óptica: ≤ 32 px usa la versión favicon, trazo {SW_FAV} u, quiebres más abiertos y sol mayor.', 64, yb2 + 30, 17)
    save('construccion.svg', W, H, ''.join(b), 'Construcción del isotipo v2',
         'Retícula y proporciones del isotipo Cordillera que late.', bg=C['crema'])

# ------------------------------------------------------------- export
def chrome_shot(html, out, w, h, transparent=True):
    page = TMP / 'p.html'; page.write_text(html, encoding='utf-8')
    raw = TMP / 'raw.png'
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
                    '--force-device-scale-factor=1', '--allow-file-access-from-files',
                    '--default-background-color=' + ('00000000' if transparent else 'ffffffff'),
                    '--user-data-dir=' + str(TMP / 'chrome'), f'--window-size={max(w, 500)},{max(h, 500)}',
                    '--virtual-time-budget=1500', '--screenshot=' + str(raw), page.as_uri()],
                   check=True, capture_output=True, timeout=90)
    with Image.open(raw) as im:
        im.crop((0, 0, w, h)).save(out)

def raster(svg_name, out, w, h):
    src = (V2 / svg_name).as_uri()
    chrome_shot('<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:transparent}'
                f'img{{display:block}}</style><img src="{src}" width="{w}" height="{h}" alt="">',
                V2 / out, w, h)

def dims(name):
    import re
    t = (V2 / name).read_text()
    m = re.search(r'width="([\d.]+)" height="([\d.]+)"', t)
    return float(m.group(1)), float(m.group(2))

def comparacion():
    v1c, v1n = (V1 / 'isotipo.svg').as_uri(), (V1 / 'isotipo-negativo.svg').as_uri()
    v1f = (V1 / 'favicon.svg').as_uri()
    v2c, v2n = (V2 / 'isotipo.svg').as_uri(), (V2 / 'isotipo-negativo.svg').as_uri()
    v2f = (V2 / 'favicon.svg').as_uri()
    def row(label, big, fav, bg, ink):
        cells = ''.join(f'<figure><img src="{big if s >= 64 else fav}" width="{s}" height="{s}"><figcaption>{s} px</figcaption></figure>'
                        for s in (512, 64, 32, 16))
        return f'<section style="background:{bg};color:{ink}"><h2>{label}</h2><div class="r">{cells}</div></section>'
    html = f'''<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:DM;src:url({(V1 / 'fonts/DMSans.ttf').as_uri()})}}
html,body{{margin:0;background:#FFF1D9;font-family:DM,sans-serif}}
.g{{display:grid;grid-template-columns:1fr 1fr;width:1600px}}
section{{padding:28px 36px 24px;height:640px;box-sizing:border-box}}
h2{{margin:0 0 18px;font-size:22px;letter-spacing:.02em}}
.r{{display:flex;align-items:flex-end;gap:34px}} figure{{margin:0;text-align:center}}
img{{display:block;margin:0 auto}} figcaption{{font-size:15px;margin-top:10px;opacity:.75}}
.foot{{grid-column:1/3;padding:14px 36px;font-size:16px;color:#06323B}}
</style><div class="g">
{row('v1 · Pulso-rayo (Codex) · sobre crema', v1c, v1f, '#FFF1D9', '#06323B')}
{row('v1 · sobre petróleo', v1n, v1f, '#06323B', '#FFF1D9')}
{row('v2 · Cordillera que late · sobre crema', v2c, v2f, '#FFF1D9', '#06323B')}
{row('v2 · sobre petróleo', v2n, v2f, '#06323B', '#FFF1D9')}
<div class="foot">A 32 y 16 px cada versión usa su favicon. v2 usa una versión compensada: trazo 12 u, quiebres más abiertos y disco petróleo.</div>
</div>'''
    chrome_shot(html, V2 / 'comparacion-v1-v2.png', 1600, 1330, transparent=False)

def hoja():
    """Hoja de revisión con todo el kit v2 (para mirar antes de entregar)."""
    items = []
    for lay in ('horizontal', 'vertical', 'isotipo', 'sello'):
        for v in ('color', 'negativo', 'negro', 'blanco'):
            name = f'{"logo-" if lay in ("horizontal", "vertical") else ""}{lay}{"" if v == "color" else "-" + v}.svg'
            bg = {'color': '#FFF1D9', 'negativo': '#06323B', 'negro': '#FFFFFF', 'blanco': '#06323B'}[v]
            w, h = dims(name)
            sc = min(340 / w, 200 / h)
            items.append(f'<figure style="background:{bg}"><img src="{(V2 / name).as_uri()}" width="{w * sc:.0f}" '
                         f'height="{h * sc:.0f}"><figcaption style="color:{"#06323B" if bg != "#06323B" else "#FFF1D9"}">{name}</figcaption></figure>')
    html = ('<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#FFF1D9;font-family:sans-serif}'
            '.g{display:grid;grid-template-columns:repeat(4,380px);gap:12px;padding:16px}'
            'figure{margin:0;height:260px;display:flex;flex-direction:column;align-items:center;justify-content:center}'
            'figcaption{font-size:12px;margin-top:8px}</style><div class="g">' + ''.join(items) + '</div>')
    chrome_shot(html, V2 / 'preview-kit-v2.png', 1568, 1130, transparent=False)

def main():
    for v in VAR:
        suf = '' if v == 'color' else '-' + v
        line, sun, _, _ = VAR[v]
        save(f'isotipo{suf}.svg', 120, 120, isotipo(12, 12, 96, line, sun),
             'Pulso Energético · isotipo', DESC[v])
        W, H, body = horizontal(v)
        save(f'logo-horizontal{suf}.svg', W, H, body, 'Pulso Energético', DESC[v])
        W, H, body = vertical(v)
        save(f'logo-vertical{suf}.svg', W, H, body, 'Pulso Energético', DESC[v])
        W, H, body = sello(v)
        save(f'sello{suf}.svg', W, H, body, 'Pulso Energético · sello Ecuador × Chile · ODS 7', DESC[v])
    save('favicon.svg', 32, 32, favicon_body(32), 'Pulso Energético', 'Favicon compensado')
    directions()
    construccion()
    raster('favicon.svg', 'favicon-32.png', 32, 32)
    w, h = dims('logo-horizontal.svg')
    raster('logo-horizontal.svg', 'logo-horizontal@2x.png', int(w * 2), int(h * 2))
    raster('construccion.svg', 'construccion.png', 1000, 1080)
    for l in 'abc':
        raster(f'direccion-{l}.svg', f'direccion-{l}.png', 960, 540)
    raster('sello.svg', 'sello.png', 960, 960)
    comparacion()
    hoja()
    shutil.rmtree(TMP, ignore_errors=True)

if __name__ == '__main__':
    main()
