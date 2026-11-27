#!/usr/bin/env python3
"""Sello «Pulso Energético» (cartel latino artesanal) en SVG vectorial.

Genera 3 niveles de detalle × 4 tratamientos. Todo el lettering se convierte
a trazados con fontTools (Fraunces OFL). La flora se dibuja UNA vez en un
sector y se replica por reflexión + rotación (simetría diédrica D4).

Uso:  python3 build_sello.py        (requiere fontTools)
"""
from math import cos, sin, radians, atan2, degrees, hypot, pi
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

HERE = Path(__file__).resolve().parent
BRAND = HERE.parent.parent
C = 500.0  # centro del lienzo 1000×1000

# ---------------------------------------------------------------- paleta
P = {
    'petroleo': '#06323B', 'noche': '#08272E', 'crema': '#FFF1D9',
    'dorado': '#FFC04C', 'verde': '#176B46', 'verde-claro': '#83D9AA',
    'terracota': '#D9643A', 'negro': '#000000',
}

# Cada elemento se pinta con un ROL; cada tratamiento asigna color a los roles.
THEMES = {
    'petroleo': dict(
        bg=P['petroleo'], ring_line=P['crema'], band=P['verde'], text=P['crema'],
        sep=P['dorado'], field=P['noche'], corona=P['dorado'], disc=P['verde'],
        disc_line=P['dorado'], disc_rays=P['dorado'], gap=P['noche'],
        bolt=P['dorado'], facet=P['crema'], ecg=P['dorado'],
        chakana=P['dorado'], chakana_cut=P['noche'], leaf=P['verde'],
        leaf2=P['verde-claro'], vein=P['noche'], vine=P['verde'],
        volute=P['crema'], fleur=P['dorado'], accent=P['terracota'],
        burst=P['dorado']),
    'crema': dict(
        bg=P['crema'], ring_line=P['petroleo'], band=P['petroleo'], text=P['crema'],
        sep=P['dorado'], field=P['crema'], corona=P['verde'], disc=P['verde'],
        disc_line=P['petroleo'], disc_rays=P['dorado'], gap=P['petroleo'],
        bolt=P['dorado'], facet=P['crema'], ecg=P['dorado'],
        chakana=P['petroleo'], chakana_cut=P['crema'], leaf=P['verde'],
        leaf2=P['verde'], vein=P['crema'], vine=P['verde'],
        volute=P['petroleo'], fleur=P['terracota'], accent=P['terracota'],
        burst=P['terracota']),
}
# Monocromo: tinta (1) o calado (0). Se resuelve con <mask> → fondo transparente real.
MONO = dict(
    bg=None, ring_line=1, band=1, text=0, sep=0, field=0, corona=1, disc=0,
    disc_line=1, disc_rays=1, gap=0, bolt=1, facet=None, ecg=1, chakana=1,
    chakana_cut=0, leaf=1, leaf2=1, vein=0, vine=1, volute=1, fleur=1,
    accent=1, burst=1)

# ---------------------------------------------------------------- geometría
def rot(p, deg, o=(0, 0)):
    a = radians(deg); x, y = p[0] - o[0], p[1] - o[1]
    return (o[0] + x * cos(a) - y * sin(a), o[1] + x * sin(a) + y * cos(a))

def polar(r, phi):
    """phi en grados desde 'arriba' (−y), horario. Origen = centro."""
    return (r * sin(radians(phi)), -r * cos(radians(phi)))

class Shape:
    """Trazado como lista de comandos con puntos; transformable afínmente."""
    def __init__(self, cmds=None):
        self.cmds = cmds or []
    def M(self, p): self.cmds.append(('M', [p])); return self
    def L(self, p): self.cmds.append(('L', [p])); return self
    def Cc(self, a, b, p): self.cmds.append(('C', [a, b, p])); return self
    def Z(self): self.cmds.append(('Z', [])); return self
    def map(self, f):
        return Shape([(c, [f(p) for p in pts]) for c, pts in self.cmds])
    def rotate(self, deg): return self.map(lambda p: rot(p, deg))
    def mirror(self): return self.map(lambda p: (-p[0], p[1]))
    def move(self, dx, dy): return self.map(lambda p: (p[0] + dx, p[1] + dy))
    def scale(self, k): return self.map(lambda p: (p[0] * k, p[1] * k))
    def d(self):
        out = []
        for c, pts in self.cmds:
            out.append(c + ' '.join(f'{x + C:.2f} {y + C:.2f}' for x, y in pts))
        return ''.join(out)

def polygon(pts):
    s = Shape().M(pts[0])
    for p in pts[1:]: s.L(p)
    return s.Z()

def catmull(pts, closed=False):
    """Curva suave (Catmull-Rom → Bézier cúbicas) que pasa por los puntos."""
    s = Shape().M(pts[0]); n = len(pts)
    for i in range(n - 1):
        p0 = pts[i - 1] if i > 0 else pts[0]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[-1]
        a = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        b = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        s.Cc(a, b, p2)
    return s

def leaf(L, W):
    """Hoja almendrada con base en (0,0) y punta en (0,−L)."""
    return (Shape().M((0, 0))
            .Cc((W * 1.05, -L * 0.22), (W * 0.85, -L * 0.72), (0, -L))
            .Cc((-W * 0.85, -L * 0.72), (-W * 1.05, -L * 0.22), (0, 0)).Z())

def petal(L, W):
    """Pétalo de gota: base aguda, remate redondo."""
    return (Shape().M((0, 0))
            .Cc((W * 0.35, -L * 0.3), (W, -L * 0.55), (W, -L * 0.78))
            .Cc((W, -L * 0.93), (W * 0.55, -L), (0, -L))
            .Cc((-W * 0.55, -L), (-W, -L * 0.93), (-W, -L * 0.78))
            .Cc((-W, -L * 0.55), (-W * 0.35, -L * 0.3), (0, 0)).Z())

def circle_shape(cx, cy, r):
    k = 0.5523 * r
    return (Shape().M((cx + r, cy))
            .Cc((cx + r, cy + k), (cx + k, cy + r), (cx, cy + r))
            .Cc((cx - k, cy + r), (cx - r, cy + k), (cx - r, cy))
            .Cc((cx - r, cy - k), (cx - k, cy - r), (cx, cy - r))
            .Cc((cx + k, cy - r), (cx + r, cy - k), (cx + r, cy)).Z())

def chakana_pts(u, steps=3, inset=0.0):
    """Cruz andina escalonada. Primer cuadrante y simetría D4.
    Un desplazamiento ortogonal hacia dentro = restar inset a |x| e |y|."""
    q = [(u, (steps + 1) * u)]
    for k in range(1, steps + 1):
        q += [(k * u, (steps + 1 - k) * u), ((k + 1) * u, (steps + 1 - k) * u)]
    q[-1] = ((steps + 1) * u, u)
    q = [(x - inset, y - inset) for x, y in q]
    full = []
    for sx, sy, rev in ((1, 1, False), (1, -1, True), (-1, -1, False), (-1, 1, True)):
        part = [(sx * x, -sy * y) for x, y in q]
        full += part[::-1] if rev else part
    return full

def spiral_pts(R, turns, tail, sense=1):
    """Voluta: cola recta + espiral logarítmica hacia dentro. Arranca en (0,0)."""
    pts = [(0, 0), (0, -tail * 0.5)]
    cx, cy = R, -tail
    n = int(18 * turns)
    for i in range(n + 1):
        t = i / n
        a = pi - t * turns * 2 * pi          # horario: sube, gira y entra
        r = R * (1 - 0.7 * t)
        pts.append((cx + r * cos(a), cy - r * sin(a)))
    return pts

# ---------------------------------------------------------------- tipografía
FONT = TTFont(BRAND / 'fonts/Fraunces.ttf')
CMAP = FONT.getBestCmap()

def glyphset(wght):
    return FONT.getGlyphSet(location={'wght': wght, 'opsz': 48, 'SOFT': 50, 'WONK': 0})

def arc_text(text, r_base, size, span_deg, where, wght):
    """Texto sobre arco convertido a trazados. where: 'top' (lee horario,
    letras hacia fuera) o 'bottom' (lee de izquierda a derecha, letras hacia el
    centro). El interletrado se calcula para llenar span_deg exactamente."""
    gs = glyphset(wght)
    k = size / FONT['head'].unitsPerEm
    names = [CMAP[ord(ch)] for ch in text]
    adv = [gs[n].width * k for n in names]
    natural = sum(adv)
    arc_len = radians(span_deg) * r_base
    track = (arc_len - natural) / (len(text) - 1)
    pen = SVGPathPen(gs)
    s = -arc_len / 2
    for n, a in zip(names, adv):
        sc = s + a / 2
        if where == 'top':
            th = -90 + degrees(sc / r_base); phi = radians(th + 90); y0 = -r_base
        else:
            th = 90 - degrees(sc / r_base); phi = radians(th - 90); y0 = r_base
        cs, sn = cos(phi), sin(phi)
        # glifo (gx,gy) → local (−a/2 + gx·k, y0 − gy·k) → rotación → centro
        xx, xy = k * cs, k * sn
        yx, yy = k * sn, -k * cs
        lx, ly = -a / 2, y0
        dx = C + lx * cs - ly * sn
        dy = C + lx * sn + ly * cs
        gs[n].draw(TransformPen(pen, (xx, xy, yx, yy, dx, dy)))
        s += a + track
    return pen.getCommands(), track / size

def cap_height(wght):
    bp = BoundsPen(glyphset(wght)); glyphset(wght)['H'].draw(bp)
    return bp.bounds[3]

# ---------------------------------------------------------------- dibujo
class Canvas:
    def __init__(self, colors):
        self.colors, self.out = colors, []
    def col(self, role):
        v = self.colors.get(role)
        if v is None: return None
        if v in (0, 1): return '#FFFFFF' if v else '#000000'
        return v
    def fill(self, role, shape_or_d, extra=''):
        c = self.col(role)
        if c is None: return
        d = shape_or_d if isinstance(shape_or_d, str) else shape_or_d.d()
        self.out.append(f'<path fill="{c}"{extra} d="{d}"/>')
    def stroke(self, role, shape, w, cap='round', join='round', extra=''):
        c = self.col(role)
        if c is None: return
        self.out.append(f'<path fill="none" stroke="{c}" stroke-width="{w:.2f}" '
                        f'stroke-linecap="{cap}" stroke-linejoin="{join}"{extra} d="{shape.d()}"/>')
    def ring(self, role, r, w):
        c = self.col(role)
        if c is None: return
        self.out.append(f'<circle cx="{C:g}" cy="{C:g}" r="{r:g}" fill="none" stroke="{c}" stroke-width="{w:g}"/>')
    def disc(self, role, r):
        c = self.col(role)
        if c is None: return
        self.out.append(f'<circle cx="{C:g}" cy="{C:g}" r="{r:g}" fill="{c}"/>')
    def group(self, label):
        self.out.append(f'<!-- {label} -->')

D4 = [0, 90, 180, 270]

def rays(cv, role, n, r0, r1, w, skip=None, alt=None):
    for i in range(n):
        a = 360 * i / n
        if skip and skip(a): continue
        ra = r0 if not alt or i % 2 == 0 else alt
        cv.stroke(role, Shape().M(polar(ra, a)).L(polar(r1, a)), w)

# --- rayo-pulso -------------------------------------------------------------
BOLT = [(40, -180), (-60, 20), (-8, 20), (-40, 185), (62, -30), (12, -30)]
FACET = [(40, -180), (-60, 20), (-49, 20), (32, -150)]  # filo iluminado

def ecg_shape(reach, simple=False):
    if simple:
        right = [(60, 0), (82, -50), (104, 0), (reach, 0)]
    else:
        right = [(58, 0), (80, -56), (100, 0), (118, 0), (134, -20), (150, 0), (reach, 0)]
    left = [(-x, -y) for x, y in right[::-1]]
    # simetría puntual: el pulso gira 180° como el rayo que lo cruza
    pts = left + right
    s = Shape().M(pts[0])
    for p in pts[1:]: s.L(p)
    return s

def taper(x0, h, length, sign):
    return polygon([(sign * x0, -h), (sign * (x0 + length), 0), (sign * x0, h)])

def draw_bolt_pulse(cv, scale=1.0, ecg_w=12, gap=7, reach=200, tip=30, simple=False):
    e = ecg_shape(reach, simple).scale(scale)
    tl, tr = taper(reach * scale - 1, ecg_w / 2, tip, -1), taper(reach * scale - 1, ecg_w / 2, tip, 1)
    bolt = polygon(BOLT).scale(scale)
    cv.group('rayo-pulso: calado de separación')
    cv.stroke('gap', e, ecg_w + 2 * gap, cap='butt')
    for t in (tl, tr):
        cv.stroke('gap', t, 2 * gap); cv.fill('gap', t)
    cv.group('línea de pulso (ECG)')
    cv.stroke('ecg', e, ecg_w, cap='butt')
    cv.fill('ecg', tl); cv.fill('ecg', tr)
    cv.group('rayo')
    cv.stroke('gap', bolt, 2 * gap * 1.15, join='miter', extra=' stroke-miterlimit="2.2"')
    cv.fill('bolt', bolt)
    if not simple:
        cv.fill('facet', polygon(FACET).scale(scale))

# --- motivo de eje: chakana + fleur ----------------------------------------
def draw_axis(cv, r_ch, u, steps, fleur=True, fleur_r=352, dot=True, cut=True):
    for a in D4:
        ch = polygon(chakana_pts(u, steps)).move(0, -r_ch).rotate(a)
        cv.fill('chakana', ch)
        if cut:
            inner = polygon(chakana_pts(u, steps, inset=u * 0.42)).move(0, -r_ch).rotate(a)
            cv.stroke('chakana_cut', inner, u * 0.22, join='miter')
        cv.fill('chakana_cut', circle_shape(0, -r_ch, u * 0.62).rotate(a))
        cv.fill('chakana', circle_shape(0, -r_ch, u * 0.28).rotate(a))
        if dot:
            cv.fill('accent', circle_shape(0, -(r_ch + (steps + 1) * u + 13), 6.5).rotate(a))
        if fleur:
            base = (0, -fleur_r)
            for ang, L, W in ((0, 40, 9.5), (-38, 29, 7.5), (38, 29, 7.5)):
                cv.fill('fleur', petal(L, W).rotate(ang).move(*base).rotate(a))

# --- motivo diagonal: flora -------------------------------------------------
def half_vine():
    return [polar(r, f) for r, f in ((214, 4), (236, 14), (266, 22), (300, 26), (334, 24), (356, 17))]

def draw_flora_full(cv):
    for a in (45, 135, 225, 315):
        for m in (False, True):
            def T(s):
                s = s.mirror() if m else s
                return s.rotate(a)
            vine_pts = half_vine()
            vine = catmull(vine_pts)
            cv.stroke('vine', T(vine), 6)
            # voluta crema al final de la guía, enroscada hacia el eje
            end = vine_pts[-1]
            ang_end = degrees(atan2(end[0] - vine_pts[-2][0], -(end[1] - vine_pts[-2][1])))
            vol = catmull(spiral_pts(17, 1.05, 12, sense=1)).rotate(ang_end + 180)
            vol = vol.mirror().move(*end)
            cv.stroke('volute', T(vol), 4.6)
            # hojas a lo largo de la guía, alternando lados
            for (r, f, ang, L, W, role) in (
                    (240, 15, -8, 46, 15, 'leaf'),
                    (262, 21, 78, 44, 14, 'leaf'),
                    (296, 26, 8, 42, 13, 'leaf'),
                    (322, 26, 100, 32, 10, 'leaf2')):
                lf = leaf(L, W).rotate(ang).move(*polar(r, f))
                cv.fill(role, T(lf))
                vein = Shape().M((0, -3)).L((0, -L * 0.78)).rotate(ang).move(*polar(r, f))
                cv.stroke('vein', T(vein), 2.2)
            # volutas crema junto a los ejes (flanquean la fleur)
            v2 = catmull(spiral_pts(17, 1.05, 18, sense=1)).rotate(160).move(*polar(372, 30))
            cv.stroke('volute', T(v2), 4.8)
            cv.fill('volute', T(circle_shape(*polar(372, 30), 4.6)))
        # hoja central sobre la diagonal + destello dorado
        cl = leaf(92, 25).move(*polar(212, 0))
        cv.fill('leaf', cl.rotate(a))
        cv.stroke('vein', Shape().M(polar(216, 0)).L(polar(290, 0)).rotate(a), 2.6)
        for k in (-2, -1, 1, 2):
            vn = Shape().M(polar(232 + 14 * abs(k) + 6, 0)).L(polar(258 + 14 * abs(k), 5.2 * (1 if k > 0 else -1))).rotate(a)
            cv.stroke('vein', vn, 1.8)
        cv.fill('accent', petal(20, 7).move(*polar(318, 0)).rotate(a))
        # destello: abanico que nace en la gota terracota (no en el centro)
        o = polar(332, 0)
        for f in (-56, -28, 0, 28, 56):
            d0, d1 = (14, 48) if f == 0 else (14, 38)
            ray = Shape().M(rot((0, -d0), f)).L(rot((0, -d1), f)).move(*o)
            cv.stroke('burst', ray.rotate(a), 4.6)

def draw_flora_simple(cv):
    for a in (45, 135, 225, 315):
        cv.fill('leaf', leaf(120, 32).move(*polar(214, 0)).rotate(a))
        cv.stroke('vein', Shape().M(polar(220, 0)).L(polar(310, 0)).rotate(a), 4)
        for m in (1, -1):
            lf = leaf(74, 22).rotate(m * 62).move(*polar(236, m * 10))
            cv.fill('leaf2', lf.rotate(a))
            v = catmull(spiral_pts(17, 1.1, 18, sense=1)).rotate(160).move(*polar(372, 26))
            v = v.mirror() if m < 0 else v
            cv.stroke('volute', v.rotate(a), 9)
        for f in (-10, 0, 10):
            cv.stroke('burst', Shape().M(polar(344, f)).L(polar(386, f)).rotate(a), 7)

# ---------------------------------------------------------------- niveles
TOP, BOTTOM = 'PULSO ENERGÉTICO', 'ECUADOR × CHILE · ODS 7'

def band_text(cv, rc, band_w, cap, wght, spans):
    k = cap / cap_height(wght) * FONT['head'].unitsPerEm / 1000  # escala aprox.
    size = cap / (cap_height(wght) / FONT['head'].unitsPerEm)
    d1, t1 = arc_text(TOP, rc - cap / 2, size, spans[0], 'top', wght)
    d2, t2 = arc_text(BOTTOM, rc + cap / 2, size, spans[1], 'bottom', wght)
    cv.fill('text', d1); cv.fill('text', d2)
    # separadores: rombo dorado con dos puntos a cada lado (9 y 3 en punto)
    for a in (90, 270):
        dia = polygon([(0, -11), (8, 0), (0, 11), (-8, 0)]).move(0, -rc).rotate(a)
        cv.fill('sep', dia)
        for off in (-3.4, 3.4):
            cv.fill('sep', circle_shape(*polar(rc, a + off), 3.2))
    return size, t1, t2

def level_completo(cv):
    cv.group('anillos y texto')
    cv.ring('ring_line', 477, 6)
    cv.ring('band', 438, 56)
    band_text(cv, 438, 56, 25, 640, (104, 128))
    cv.ring('ring_line', 404, 5)
    cv.disc('field', 401.5)
    cv.group('flora (D4: un sector reflejado y rotado)')
    draw_flora_full(cv)
    cv.group('chakanas y fleurs en los ejes')
    draw_axis(cv, 280, 12, 3)
    cv.group('sol central')
    rays(cv, 'corona', 72, 183, 199, 2.6)
    cv.disc('disc', 165)
    cv.ring('disc_line', 172, 3.2)
    rays(cv, 'disc_rays', 40, 96, 150, 3.6, alt=120)
    draw_bolt_pulse(cv, reach=184, tip=26)

def level_simple(cv):
    cv.ring('ring_line', 478, 8)
    cv.ring('band', 432, 72)
    band_text(cv, 432, 72, 36, 780, (122, 150))
    cv.ring('ring_line', 391, 7)
    cv.disc('field', 388)
    draw_flora_simple(cv)
    draw_axis(cv, 274, 15, 3, fleur=False, dot=False)
    rays(cv, 'corona', 36, 184, 204, 5)
    cv.disc('disc', 166)
    rays(cv, 'disc_rays', 16, 104, 148, 7)
    draw_bolt_pulse(cv, scale=1.02, ecg_w=17, gap=9, reach=192, tip=26, simple=True)

def level_mini(cv):
    cv.ring('band', 440, 72)
    cv.disc('field', 404)
    draw_axis(cv, 292, 26, 2, fleur=False, dot=False, cut=False)
    draw_bolt_pulse(cv, scale=1.15, ecg_w=30, gap=12, reach=140, tip=22, simple=True)

LEVELS = {'completo': level_completo, 'simple': level_simple, 'mini': level_mini}
DESC = {
    'completo': 'Nivel hero: portada, video, OG, sticker grande (≥ 512 px).',
    'simple': 'Nivel reducido: avatar y badge 128–256 px; menos flora, trazos más gruesos.',
    'mini': 'Nivel mínimo 32–64 px: anillo, cuatro chakanas y rayo-pulso.',
}

def build(level, theme):
    if theme in THEMES:
        colors = THEMES[theme]
        cv = Canvas(colors); LEVELS[level](cv)
        body = f'<rect width="1000" height="1000" fill="{colors["bg"]}"/>' + ''.join(cv.out)
    else:
        ink = P['dorado'] if theme == 'dorado' else P['negro']
        cv = Canvas(MONO); LEVELS[level](cv)
        bg = f'<rect width="1000" height="1000" fill="{P["petroleo"]}"/>' if theme == 'dorado' else ''
        body = (f'<defs><mask id="tinta-{level}" maskUnits="userSpaceOnUse" x="0" y="0" width="1000" height="1000">'
                '<rect width="1000" height="1000" fill="#000"/>' + ''.join(cv.out) +
                f'</mask></defs>{bg}<rect width="1000" height="1000" fill="{ink}" mask="url(#tinta-{level})"/>')
    names = {'petroleo': 'color sobre petróleo', 'crema': 'color sobre crema',
             'dorado': 'monocromo dorado sobre petróleo', 'negro': 'monocromo negro (fondo transparente)'}
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000" '
            f'role="img" aria-labelledby="t d"><title id="t">Sello Pulso Energético · {level} · {names[theme]}</title>'
            f'<desc id="d">Sello cartel latino: anillo con «PULSO ENERGÉTICO» y «ECUADOR × CHILE · ODS 7», '
            f'cuatro chakanas, flora en simetría D4 y rayo-pulso dorado. {DESC[level]}</desc>\n{body}\n</svg>\n')

if __name__ == '__main__':
    for level in LEVELS:
        for theme in ('petroleo', 'crema', 'dorado', 'negro'):
            name = f'sello-{level}.svg' if theme == 'petroleo' else f'sello-{level}-{theme}.svg'
            (HERE / name).write_text(build(level, theme), encoding='utf-8')
            print('ok', name)
