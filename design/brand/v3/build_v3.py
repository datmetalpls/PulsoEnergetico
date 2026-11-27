#!/usr/bin/env python3
"""Genera la marca v3 «Casa que late» de Pulso Energético.

Uso:  python3 build_v3.py   (solo escribe dentro de design/brand/v3/)
Requiere fontTools, Pillow y Google Chrome. Todo el texto de los SVG va a trazados.
"""
from pathlib import Path
import math, re, subprocess, tempfile, shutil
from PIL import Image
from fontTools.pens.boundsPen import BoundsPen
import marca
from marca import (C, isotipo, word, caps_on_arc, svg_doc, rounded, glyphset, _sans,
                   H_PTS, F_PTS, SUN, SUN_FAV, SW, SW_FAV, GAP, BASE, DOOR, _segdist)

V3 = Path(__file__).resolve().parent
BRAND = V3.parent
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
TMP = Path(tempfile.mkdtemp(prefix='pe-v3-'))
WM = 'Pulso Energético'
CAP_TOP = 50

def save(name, w, h, body, title, desc='', bg=None):
    (V3 / name).write_text(svg_doc(w, h, body, title, desc, bg), encoding='utf-8')

def es(n):
    return f'{n:g}'.replace('.', ',')

def sans(text, x, y, size, fill, wght=500, track=0):
    return word(text, x, y, size, fill, loc={'wght': wght, 'opsz': 14}, kern={}, track=track,
                font=_sans)

def cap_height():
    gs, cmap = glyphset()
    bp = BoundsPen(gs); gs[cmap[ord('P')]].draw(bp)
    return bp.bounds[3] / 2000

# (trazo, sol, puerta, tilde, texto)
VAR = {
    'color':    (C['petroleo'], C['dorado'], C['verde'], C['ambar'], C['petroleo']),
    'negativo': (C['crema'], C['dorado'], C['verde-claro'], C['dorado'], C['crema']),
    'negro':    (C['negro'],) * 5,
    'blanco':   (C['blanco'],) * 5,
}
DESC = {'color': 'Color sobre crema', 'negativo': 'Negativo sobre petróleo',
        'negro': 'Una tinta negra', 'blanco': 'Una tinta blanca'}

def iso(x, y, s, v, **kw):
    line, sun, door, _, _ = VAR[v]
    return isotipo(x, y, s, line, sun, door=door, **kw)

def wordmark(x, y, size, v):
    _, _, _, tilde, ink = VAR[v]
    return word(WM, x, y, size, ink, tilde=tilde)

def horizontal(v):
    s = 120; ix, iy = 24, 20
    base = iy + s * BASE / 96            # el texto se apoya en el suelo de la casa
    eave = iy + s * CAP_TOP / 96              # altura de mayúscula = 38 u del lienzo
    size = (base - eave) / cap_height()
    wm, w = wordmark(ix + s + 18, base, size, v)
    return math.ceil(ix + s + 18 + w + 28), 160, iso(ix, iy, s, v) + wm

def vertical(v):
    size = 62
    w = word(WM, 0, 0, size, '#000', tilde='#000')[1]
    W = math.ceil(w + 64); s = 180
    body = iso((W - s) / 2, 24, s, v)
    wm, _ = wordmark((W - w) / 2, 24 + s + 62, size, v)
    return W, 24 + s + 62 + 40, body + wm

def star4(cx, cy, r, fill):
    k = r * .28
    pts = [(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k), (cx, cy + r),
           (cx - k, cy + k), (cx - r, cy), (cx - k, cy - k)]
    return (f'<path d="M{"L".join(f"{a:.2f} {b:.2f}" for a, b in pts)}Z" fill="{fill}" '
            f'stroke="{fill}" stroke-width="{r * .12:.2f}" stroke-linejoin="round"/>')

def sello(v):
    W = 480; c = 240
    if v == 'color':
        disk, ink, acc, iv = C['petroleo'], C['crema'], C['dorado'], 'negativo'
    elif v == 'negativo':
        disk, ink, acc, iv = None, C['crema'], C['dorado'], 'negativo'
    else:
        disk, ink, acc, iv = None, C[v], C[v], v
    b = []
    if disk:
        b.append(f'<circle cx="{c}" cy="{c}" r="230" fill="{disk}"/>')
    b.append(f'<circle cx="{c}" cy="{c}" r="221" fill="none" stroke="{acc}" stroke-width="3"/>')
    b.append(f'<circle cx="{c}" cy="{c}" r="166" fill="none" stroke="{ink}" stroke-width="2"/>')
    for i in range(72):
        a = i * 5
        if 60 < a < 120 or 240 < a < 300:
            continue
        ar = math.radians(a)
        b.append(f'<circle cx="{c + 159 * math.sin(ar):.2f}" cy="{c - 159 * math.cos(ar):.2f}" '
                 f'r="{1.6 if i % 3 else 2.4}" fill="{acc}"/>')
    loc = {'wght': 700, 'opsz': 72, 'SOFT': 50, 'WONK': 0}
    b.append(caps_on_arc('ECUADOR × CHILE · ODS 7', c, c, 182, 34, ink, 0, loc=loc, track=150))
    b.append(caps_on_arc('PULSO ENERGÉTICO', c, c, 207, 34, ink, 180, loc=loc, track=170, bottom=True))
    b.append(star4(c - 194, c, 11, acc)); b.append(star4(c + 194, c, 11, acc))
    s = 232
    b.append(iso(c - s / 2, c - s / 2 - 4, s, iv))
    return W, W, ''.join(b)

def favicon_body(size=32):
    k = size / 96
    clip = marca.uid('fav')
    return (f'<defs><clipPath id="{clip}"><circle cx="{48 * k}" cy="{48 * k}" r="{48 * k}"/></clipPath></defs>'
            f'<circle cx="{48 * k}" cy="{48 * k}" r="{48 * k}" fill="{C["petroleo"]}"/>'
            f'<g clip-path="url(#{clip})">' + iso(0, 0, size, 'negativo', favicon=True) + '</g>')

def og_image():
    W, H = 1200, 630
    b = [f'<rect width="{W}" height="{H}" fill="{C["petroleo"]}"/>']
    b.append(sans('HACKATÓN ECUADOR × CHILE · ODS 7', 80, 104, 22, C['dorado'], 700, track=140)[0])
    b.append(iso(80, 150, 120, 'negativo'))
    base = 150 + 120 * BASE / 96
    size = (120 * (BASE - CAP_TOP) / 96) / cap_height()
    b.append(wordmark(80 + 120 + 18, base, size, 'negativo')[0])
    b.append(word('La energía de tu sede,', 80, 392, 58, C['crema'])[0])
    b.append(word('a la vista.', 80, 458, 58, C['crema'])[0])
    b.append(sans('Cuenca · Puente Alto', 80, 520, 22, C['dorado'], 500)[0])
    b.append(f'<path d="M80 548H{W - 80}" stroke="{C["dorado"]}" stroke-opacity=".7" stroke-width="2"/>')
    b.append(sans('Prototipo con datos simulados', 80, 584, 18, C['crema'], 400)[0])
    # sello de esquina
    sw_, sh_, sb = sello('negativo')
    b.append(f'<g transform="translate({W - 80 - 300} 120) scale({300 / 480})">{sb}</g>')
    save('og-image-1200x630.svg', W, H, ''.join(b), 'Pulso Energético · La energía de tu sede, a la vista.',
         'Imagen para compartir')

def apple_touch():
    body = f'<rect width="180" height="180" fill="{C["petroleo"]}"/>' + iso(26, 22, 128, 'negativo')
    save('apple-touch-icon.svg', 180, 180, body, 'Pulso Energético', 'Ícono para iOS')

# ------------------------------------------------------------- construcción
def construccion():
    W, H = 1160, 1120; k = 8; ox, oy = 250, 150
    P = lambda x, y: (ox + x * k, oy + y * k)
    b = []
    for i in range(0, 97, 4):
        op = .28 if i % 24 == 0 else (.14 if i % 8 == 0 else .06)
        b.append(f'<path d="M{ox + i * k} {oy}V{oy + 96 * k}M{ox} {oy + i * k}H{ox + 96 * k}" '
                 f'stroke="{C["petroleo"]}" stroke-opacity="{op}" stroke-width="1"/>')
    b.append(f'<rect x="{ox}" y="{oy}" width="{96 * k}" height="{96 * k}" fill="none" stroke="{C["petroleo"]}" stroke-opacity=".45"/>')
    b.append(iso(ox, oy, 96 * k, 'color'))
    red = '#B42318'
    cx, cy, r = SUN
    X, Y = P(cx, cy)
    b.append(f'<path d="M{X - 9} {Y}H{X + 9}M{X} {Y - 9}V{Y + 9}" stroke="{C["petroleo"]}" stroke-width="2"/>')
    # aire uniforme: perpendiculares a las dos laderas
    for a, bb in ((H_PTS[4], H_PTS[5]), (H_PTS[7], H_PTS[8])):
        (ax, ay), (bx, by) = a, bb
        dx, dy = bx - ax, by - ay; L = math.hypot(dx, dy)
        t = ((cx - ax) * dx + (cy - ay) * dy) / (L * L)
        fx, fy = ax + t * dx, ay + t * dy
        ux, uy = (fx - cx) / math.hypot(fx - cx, fy - cy), (fy - cy) / math.hypot(fx - cx, fy - cy)
        p1 = P(cx + ux * r, cy + uy * r); p2 = P(cx + ux * (r + GAP), cy + uy * (r + GAP))
        b.append(f'<path d="M{p1[0]:.1f} {p1[1]:.1f}L{p2[0]:.1f} {p2[1]:.1f}" stroke="{red}" stroke-width="3"/>')
        b.append(f'<circle cx="{p1[0]:.1f}" cy="{p1[1]:.1f}" r="3" fill="{red}"/><circle cx="{p2[0]:.1f}" cy="{p2[1]:.1f}" r="3" fill="{red}"/>')
    yb = oy + BASE * k
    b.append(f'<path d="M{ox - 60} {yb}H{ox + 96 * k + 60}" stroke="{red}" stroke-width="1.5" stroke-dasharray="10 6"/>')
    ye = oy + CAP_TOP * k
    b.append(f'<path d="M{ox - 60} {ye}H{ox + 96 * k + 60}" stroke="{C["ambar"]}" stroke-width="1.5" stroke-dasharray="4 6"/>')
    for (x, y) in H_PTS:
        px, py = P(x, y)
        b.append(f'<circle cx="{px}" cy="{py}" r="6" fill="{C["crema"]}" stroke="{red}" stroke-width="2"/>')
    def lab(t, x, y, size=16, color=C['petroleo'], wght=500, chip=False):
        svg_, w_ = sans(t, x, y, size, color, wght)
        if chip:
            b.append(f'<rect x="{x - 5:.1f}" y="{y - size * .95:.1f}" width="{w_ + 10:.1f}" height="{size * 1.35:.1f}" rx="4" fill="{C["crema"]}" fill-opacity=".92"/>')
        b.append(svg_)
    def leader(x1, y1, x2, y2):
        b.append(f'<path d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}" stroke="{C["petroleo"]}" stroke-width="1.2"/>')
    lab('Construcción del isotipo v3 · «Casa que late»', 64, 64, 26, wght=700)
    lab('Lienzo 96 u · módulo 8 u · retícula mayor 24 u · un solo trazo con uniones y remates redondeados', 64, 98, 17)
    L = 40  # margen izquierdo de etiquetas
    lab(f'suelo y = {BASE}', L, yb - 18, 16, red, 600); lab('línea base del texto', L, yb + 4, 14, red)
    lab(f'y = {CAP_TOP}', L, ye - 18, 16, C['ambar'], 600); lab('altura de mayúscula', L, ye + 4, 14, C['ambar'])
    px, py = P(28, 14); lab('cumbre Ecuador (28, 14)', L, py + 5, 15); leader(L + 178, py, px - 40, py)
    px, py = P(44.5, 48); lab('escalón del rayo', L, py - 60, 15, wght=600); leader(L + 128, py - 65, px - 34, py - 4)
    px, py = P(70, 18); lab('cumbre Chile (70, 18)', px + 52, py + 5, 15, chip=True)
    px, py = P(52, 64); lab('latido (52, 64)', P(56, 0)[0], py + 30, 15, chip=True); leader(px + 8, py + 8, P(56, 0)[0] - 4, py + 24)
    lab(f'sol: centro x {es(cx)} · y {es(cy)} · r = {es(r)} u', X + r * k + 60, oy + 34, 16, C['ambar'], 600, chip=True)
    lab(f'aire uniforme {es(GAP)} u a ambas laderas', X + r * k + 60, oy + 58, 16, red, 600, chip=True)
    dx_, dr, dtop = DOOR
    px, py = P(dx_ + dr, dtop + 8); lab(f'puerta r = {es(dr)} u', px + 14, py + 5, 14, chip=True)
    y2 = oy + 96 * k + 64
    lab(f'Trazo {es(SW)} u · el sol es equidistante (r + trazo/2 + aire) de la ladera Ecuador y la ladera Chile: nunca muerde el trazo.', 64, y2, 16)
    lab(f'Favicon (≤ 32 px): sin escalón, picos simétricos, trazo {es(SW_FAV)} u, puerta y sol mayores, disco petróleo.', 64, y2 + 28, 16)
    save('construccion.svg', W, H, ''.join(b), 'Construcción del isotipo v3',
         'Retícula y proporciones de la casa que late.', bg=C['crema'])

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
    chrome_shot('<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:transparent}'
                f'img{{display:block}}</style><img src="{(V3 / svg_name).as_uri()}" width="{w}" height="{h}" alt="">',
                V3 / out, w, h)

def dims(name):
    m = re.search(r'width="([\d.]+)" height="([\d.]+)"', (V3 / name).read_text())
    return float(m.group(1)), float(m.group(2))

def comparacion():
    sets = [
        ('v1 · Pulso-rayo', BRAND / 'isotipo.svg', BRAND / 'isotipo-negativo.svg', BRAND / 'favicon.svg'),
        ('v2 · Cordillera que late', BRAND / 'v2/isotipo.svg', BRAND / 'v2/isotipo-negativo.svg', BRAND / 'v2/favicon.svg'),
        ('v3 · Casa que late (final)', V3 / 'isotipo.svg', V3 / 'isotipo-negativo.svg', V3 / 'favicon.svg'),
    ]
    def row(label, big, fav, bg, ink):
        cells = ''.join(f'<figure><img src="{(big if s >= 64 else fav).as_uri()}" width="{s}" height="{s}">'
                        f'<figcaption>{s} px</figcaption></figure>' for s in (512, 64, 32, 16))
        return f'<section style="background:{bg};color:{ink}"><h2>{label}</h2><div class="r">{cells}</div></section>'
    rows = ''.join(row(l + ' · sobre crema', c, f, '#FFF1D9', '#06323B') + row(l + ' · sobre petróleo', n, f, '#06323B', '#FFF1D9')
                   for l, c, n, f in sets)
    html = f'''<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:DM;src:url({(BRAND / 'fonts/DMSans.ttf').as_uri()})}}
html,body{{margin:0;background:#FFF1D9;font-family:DM,sans-serif}}
.g{{display:grid;grid-template-columns:1fr 1fr;width:1600px}}
section{{padding:24px 36px 20px;height:620px;box-sizing:border-box}}
h2{{margin:0 0 14px;font-size:22px}}
.r{{display:flex;align-items:flex-end;gap:34px}} figure{{margin:0;text-align:center}}
img{{display:block;margin:0 auto}} figcaption{{font-size:15px;margin-top:10px;opacity:.75}}
.foot{{grid-column:1/3;padding:14px 36px;font-size:16px;color:#06323B}}
</style><div class="g">{rows}
<div class="foot">A 32 y 16 px cada versión usa su favicon. v3 usa una casa compensada: sin escalón del rayo, picos simétricos, trazo 12,5 u y disco petróleo.</div></div>'''
    chrome_shot(html, V3 / 'comparacion-v1-v2-v3.png', 1600, 1920, transparent=False)

def hoja():
    items = []
    for lay in ('horizontal', 'vertical', 'isotipo', 'sello'):
        for v in VAR:
            name = f'{"logo-" if lay in ("horizontal", "vertical") else ""}{lay}{"" if v == "color" else "-" + v}.svg'
            bg = {'color': '#FFF1D9', 'negativo': '#06323B', 'negro': '#FFFFFF', 'blanco': '#06323B'}[v]
            w, h = dims(name); sc = min(340 / w, 200 / h)
            items.append(f'<figure style="background:{bg}"><img src="{(V3 / name).as_uri()}" width="{w * sc:.0f}" '
                         f'height="{h * sc:.0f}"><figcaption style="color:{"#FFF1D9" if bg == "#06323B" else "#06323B"}">{name}</figcaption></figure>')
    html = ('<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#FFF1D9;font-family:sans-serif}'
            '.g{display:grid;grid-template-columns:repeat(4,380px);gap:12px;padding:16px}'
            'figure{margin:0;height:260px;display:flex;flex-direction:column;align-items:center;justify-content:center}'
            'figcaption{font-size:12px;margin-top:8px}</style><div class="g">' + ''.join(items) + '</div>')
    chrome_shot(html, V3 / 'preview-kit-v3.png', 1568, 1130, transparent=False)

def main():
    for v in VAR:
        suf = '' if v == 'color' else '-' + v
        save(f'isotipo{suf}.svg', 120, 120, iso(12, 12, 96, v), 'Pulso Energético · isotipo', DESC[v])
        W, H, body = horizontal(v)
        save(f'logo-horizontal{suf}.svg', W, H, body, 'Pulso Energético', DESC[v])
        W, H, body = vertical(v)
        save(f'logo-vertical{suf}.svg', W, H, body, 'Pulso Energético', DESC[v])
        W, H, body = sello(v)
        save(f'sello{suf}.svg', W, H, body, 'Pulso Energético · sello Ecuador × Chile · ODS 7', DESC[v])
    save('favicon.svg', 32, 32, favicon_body(32), 'Pulso Energético', 'Favicon compensado')
    apple_touch(); og_image(); construccion()
    raster('favicon.svg', 'favicon-32.png', 32, 32)
    raster('apple-touch-icon.svg', 'apple-touch-icon-180.png', 180, 180)
    raster('og-image-1200x630.svg', 'og-image-1200x630.png', 1200, 630)
    for v in VAR:
        suf = '' if v == 'color' else '-' + v
        w, h = dims(f'logo-horizontal{suf}.svg')
        raster(f'logo-horizontal{suf}.svg', f'logo-horizontal{suf}@2x.png', int(w * 2), int(h * 2))
        w, h = dims(f'logo-vertical{suf}.svg')
        raster(f'logo-vertical{suf}.svg', f'logo-vertical{suf}@2x.png', int(w * 2), int(h * 2))
        raster(f'isotipo{suf}.svg', f'isotipo{suf}@2x.png', 240, 240)
        raster(f'sello{suf}.svg', f'sello{suf}@2x.png', 960, 960)
    raster('construccion.svg', 'construccion.png', 1160, 1120)
    comparacion(); hoja()
    shutil.rmtree(TMP, ignore_errors=True)

if __name__ == '__main__':
    main()
