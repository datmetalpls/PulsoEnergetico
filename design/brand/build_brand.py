#!/usr/bin/env python3
"""Rebuild vector brand assets and verify WCAG contrast; needs fontTools.

Fonts are original OFL files. All visible SVG lettering is converted to paths.
"""
from pathlib import Path
from html import escape
import json
import xml.etree.ElementTree as ET
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = Path(__file__).resolve().parent
COLORS = {
    'petroleo': '#06323B', 'crema': '#FFF1D9', 'dorado': '#FFC04C',
    'verde': '#176B46', 'verde-claro': '#83D9AA', 'alerta': '#B42318',
    'alerta-clara': '#FF9B91', 'alerta-fondo': '#FDECE9',
    'alerta-fondo-noche': '#421915', 'tinta': '#132F33',
    'texto-secundario': '#455F60', 'blanco': '#FFFFFF', 'negro': '#000000',
    'tarde': '#F3DFC0', 'noche': '#08272E', 'superficie-noche': '#103D46',
    'dorado-texto': '#805000', 'foco': '#005FCC', 'foco-noche': '#8BCCFF',
}
FONTS = {
    'serif': TTFont(ROOT / 'fonts/Fraunces.ttf'),
    'sans': TTFont(ROOT / 'fonts/DMSans.ttf'),
}

def lettering(text, x, y, size, color, family='serif', weight=650):
    font = FONTS[family]
    glyphs = font.getGlyphSet(location={'wght': weight, 'opsz': 24})
    cmap = font.getBestCmap()
    scale = size / font['head'].unitsPerEm
    pen = SVGPathPen(glyphs)
    cursor = 0
    for char in text:
        glyph = glyphs[cmap[ord(char)]]
        glyph.draw(TransformPen(pen, (scale, 0, 0, -scale, x + cursor * scale, y)))
        cursor += glyph.width
    return f'<path fill="{color}" d="{pen.getCommands()}"/>'

def icon(x=0, y=0, size=112, variant='color'):
    bg, pulse = COLORS['petroleo'], COLORS['dorado']
    if variant in ('negro', 'blanco'):
        bg = COLORS[variant]
        return (f'<g transform="translate({x} {y}) scale({size/112})">'
                '<defs><mask id="pulse-cut"><rect width="112" height="112" fill="white"/>'
                '<path d="M18 61H35L54 29L48 53H73L54 84L60 61H94" '
                'fill="none" stroke="black" stroke-width="8" stroke-linejoin="round" stroke-linecap="round"/>'
                '</mask></defs>'
                f'<rect width="112" height="112" rx="27" fill="{bg}" mask="url(#pulse-cut)"/></g>')
    if variant == 'negativo':
        bg, pulse = COLORS['dorado'], COLORS['petroleo']
    return (f'<g transform="translate({x} {y}) scale({size/112})">'
            f'<rect width="112" height="112" rx="27" fill="{bg}"/>'
            f'<path d="M18 61H35L54 29L48 53H73L54 84L60 61H94" fill="none" '
            f'stroke="{pulse}" stroke-width="8" stroke-linejoin="round" stroke-linecap="round"/></g>')

def svg(width, height, content, title, desc=''):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>{content}</svg>')

def save(name, width, height, content, title, desc=''):
    (ROOT / name).write_text(svg(width, height, content, title, desc), encoding='utf-8')

def logo(layout, variant):
    ink = COLORS['crema'] if variant == 'negativo' else COLORS['petroleo']
    if variant in ('negro', 'blanco'):
        ink = COLORS[variant]
    if layout == 'horizontal':
        return 720, 160, icon(24, 24, 112, variant) + lettering('Pulso Energético', 160, 100, 49, ink)
    if layout == 'vertical':
        return 400, 304, (icon(144, 24, 112, variant) + lettering('Pulso', 134, 204, 48, ink)
                           + lettering('Energético', 77, 260, 48, ink))
    return 160, 160, icon(24, 24, 112, variant)

def luminance(hexcolor):
    channels = [int(hexcolor[i:i+2], 16) / 255 for i in (1, 3, 5)]
    rgb = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
    return sum(c * k for c, k in zip(rgb, (.2126, .7152, .0722)))

def contrast(a, b):
    light, dark = sorted([luminance(a), luminance(b)], reverse=True)
    return (light + .05) / (dark + .05)

def main():
    for layout in ('horizontal', 'vertical', 'isotipo'):
        stem = 'isotipo' if layout == 'isotipo' else 'logo-' + layout
        for variant in ('color', 'negativo', 'negro', 'blanco'):
            w, h, content = logo(layout, variant)
            suffix = '' if variant == 'color' else '-' + variant
            save(stem + suffix + '.svg', w, h, content, 'Pulso Energético',
                 f'Pulso-rayo. Versión {variant}; área de seguridad incluida: 24 unidades.')
    save('favicon.svg', 112, 112, icon(), 'Pulso Energético')

    concepts = [
        ('Pulso-rayo', 'Un pulso angular forma un rayo: energía que se puede seguir.', icon(40, 40, 144)),
        ('Conexión compartida', 'Un enchufe reúne dos ondas: dos localidades, una lectura común.',
         '<g fill="none" stroke="#06323B" stroke-width="9" stroke-linecap="round" stroke-linejoin="round">'
         '<path d="M82 84V52M134 84V52M69 84H147V109Q147 147 108 147Q69 147 69 109Z"/>'
         '<path d="M108 147V169H157"/><path d="M79 115Q93 95 108 115T137 115" stroke="#805000"/></g>'),
        ('Luz con límite', 'Un sol abierto cruza una línea de umbral: ver el margen disponible.',
         '<g fill="none" stroke="#06323B" stroke-width="9" stroke-linecap="round">'
         '<path d="M61 128A50 50 0 1 1 145 128M85 151H131M91 166H125"/>'
         '<path d="M108 37V23M54 58L43 47M162 58L173 47M37 108H23M179 108H193"/>'
         '<path d="M55 128H161" stroke="#805000" stroke-dasharray="10 9"/></g>'),
    ]
    for n, (name, idea, drawing) in enumerate(concepts, 1):
        content = '<rect width="860" height="232" fill="#FFF1D9"/>' + drawing
        content += lettering(f'0{n} / {name}', 226, 89, 34, COLORS['petroleo'])
        # The one-line explanation is also accessible as SVG metadata.
        content += lettering('Pulso Energético', 226, 137, 25, COLORS['petroleo'], 'sans', 600)
        content += lettering(idea, 226, 180, 16, COLORS['petroleo'], 'sans', 500)
        save(f'concepts/concepto-{n}.svg', 860, 232, content, name, idea)

    og = '<rect width="1200" height="630" fill="#06323B"/>'
    og += '<path d="M66 541H1134" stroke="#FFC04C" stroke-width="2"/>'
    og += lettering('HACKATÓN ECUADOR × CHILE · ODS 7', 68, 72, 21, COLORS['dorado'], 'sans', 700)
    og += icon(68, 135, 130, 'negativo')
    og += lettering('Pulso Energético', 236, 224, 67, COLORS['crema'])
    og += lettering('La energía de tu sede,', 68, 350, 58, COLORS['crema'])
    og += lettering('a la vista.', 68, 420, 58, COLORS['crema'])
    og += lettering('Cuenca · Puente Alto', 68, 501, 25, COLORS['dorado'], 'sans', 500)
    og += lettering('Prototipo con datos simulados', 68, 584, 21, COLORS['crema'], 'sans', 500)
    save('og-image-1200x630.svg', 1200, 630, og, 'Pulso Energético', 'Hackatón Ecuador × Chile · ODS 7. Prototipo con datos simulados.')

    # Every surface has an explicit AA text pair; decorative gold is not body text on cream.
    text_on = {
        'petroleo':'crema', 'crema':'petroleo', 'dorado':'petroleo', 'verde':'blanco',
        'verde-claro':'petroleo', 'alerta':'blanco', 'alerta-clara':'petroleo',
        'alerta-fondo':'alerta', 'alerta-fondo-noche':'alerta-clara', 'tinta':'crema',
        'texto-secundario':'blanco', 'blanco':'petroleo', 'negro':'blanco', 'tarde':'petroleo',
        'noche':'crema', 'superficie-noche':'crema', 'dorado-texto':'crema',
        'foco':'blanco', 'foco-noche':'petroleo',
    }
    results = []
    for bg, fg in text_on.items():
        ratio = contrast(COLORS[fg], COLORS[bg])
        assert ratio >= 4.5, (fg, bg, ratio)
        results.append({'background':bg, 'foreground':fg, 'ratio':round(ratio, 3), 'AA_normal':True})
    for bg in ('crema', 'blanco', 'tarde'):
        for fg in ('petroleo', 'texto-secundario', 'verde', 'alerta', 'dorado-texto', 'foco'):
            ratio = contrast(COLORS[fg], COLORS[bg])
            assert ratio >= 4.5, (fg, bg, ratio)
            results.append({'background':bg, 'foreground':fg, 'ratio':round(ratio, 3), 'AA_normal':True})
    for bg in ('petroleo', 'noche', 'superficie-noche'):
        for fg in ('crema', 'dorado', 'verde-claro', 'alerta-clara', 'foco-noche'):
            ratio = contrast(COLORS[fg], COLORS[bg])
            assert ratio >= 4.5, (fg, bg, ratio)
            results.append({'background':bg, 'foreground':fg, 'ratio':round(ratio, 3), 'AA_normal':True})
    assert abs(contrast('#000000', '#FFFFFF') - 21) < 1e-9
    assert contrast(COLORS['dorado'], COLORS['crema']) < 3
    data = {'name':'Pulso Energético', 'colors':COLORS, 'contrast':results,
            'standard':'WCAG 2.x relative sRGB luminance; AA normal text ≥ 4.5:1; UI ≥ 3:1',
            'warning':'Dorado sobre crema no cumple AA; usar dorado-texto. Verde es semántico propio, no color oficial del ODS 7 (amarillo).'}
    (ROOT / 'tokens.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    css = '/* Pulso Energético · Ver pares AA en tokens.json; no remapear temas globalmente. */\n:root {\n'
    css += ''.join(f'  --pe-{key}: {value};\n' for key, value in COLORS.items())
    css += '  --pe-font-titular: "Fraunces", Georgia, serif;\n  --pe-font-ui: "DM Sans", system-ui, sans-serif;\n}\n'
    (ROOT / 'tokens.css').write_text(css)
    (ROOT / 'contrast-report.json').write_text(json.dumps({'checks_passed':len(results), 'pairs':results}, indent=2))
    files = list(ROOT.rglob('*.svg'))
    for path in files:
        tree = ET.parse(path)
        assert tree.getroot().tag == '{http://www.w3.org/2000/svg}svg'
        assert not tree.findall('.//{http://www.w3.org/2000/svg}text'), path
        assert 'https://' not in path.read_text(), path
    print(f'PASS: {len(files)} SVG XML, text converted to paths; {len(results)} contrast pairs AA; black/white = 21:1.')

if __name__ == '__main__':
    main()
