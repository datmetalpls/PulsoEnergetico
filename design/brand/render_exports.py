#!/usr/bin/env python3
"""Rasterize local SVGs and the manual with installed Chrome headless.

No external runtime resources; all temporary browser files stay under brand/.
"""
from pathlib import Path
from html import escape
import subprocess
import shutil
from PIL import Image
from build_brand import save, icon

ROOT = Path(__file__).resolve().parent
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

def chrome(*args):
    subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
                    '--no-first-run', '--no-default-browser-check', '--hide-scrollbars',
                    '--allow-file-access-from-files', '--disable-background-networking',
                    '--disable-component-update', '--force-device-scale-factor=1',
                    '--default-background-color=00000000',
                    '--user-data-dir=' + str(ROOT / '.chrome-profile'), *args],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40)

def raster(source, output, width, height):
    page = ROOT / '.export.html'
    page.write_text('<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:transparent}img{display:block}</style>'
                    f'<img src="{escape(source)}" width="{width}" height="{height}" alt="">')
    raw = ROOT / '.export.png'
    chrome('--window-size=' + str(max(800, width)) + ',' + str(max(800, height)),
           '--virtual-time-budget=1500', '--screenshot=' + str(raw), page.as_uri())
    with Image.open(raw) as image:
        assert image.width >= width and image.height >= height
        image.crop((0, 0, width, height)).save(ROOT / output)
    raw.unlink()
    page.unlink()

def main():
    save('apple-touch-icon.svg', 180, 180,
         '<rect width="180" height="180" fill="#FFF1D9"/>' + icon(20, 20, 140),
         'Pulso Energético')
    exports = [('favicon.svg', 'favicon-32.png', 32, 32),
               ('apple-touch-icon.svg', 'apple-touch-icon-180.png', 180, 180),
               ('og-image-1200x630.svg', 'og-image-1200x630.png', 1200, 630),
               ('logo-horizontal.svg', 'logo-horizontal-1x.png', 720, 160),
               ('logo-horizontal.svg', 'logo-horizontal-2x.png', 1440, 320)]
    for spec in exports:
        raster(*spec)
    manual = (ROOT / 'manual.html').as_uri()
    chrome('--window-size=1120,1750', '--virtual-time-budget=3000',
           '--screenshot=' + str(ROOT / 'preview-manual.png'), manual)
    chrome('--virtual-time-budget=3000', '--no-pdf-header-footer',
           '--print-to-pdf=' + str(ROOT / 'manual.pdf'), manual)
    # A contact sheet lets a reviewer inspect raster sizes and both dark and light variants.
    page = ROOT / 'preview-kit.html'
    items = ['<section><h2>' + escape(name) + '</h2><img src="' + escape(name) +
             '" style="width:' + ('32px' if name == 'favicon-32.png' else 'min(100%,660px)') + '"></section>'
             for name in ['logo-horizontal-1x.png', 'logo-horizontal-negativo.svg',
                          'logo-horizontal-negro.svg', 'logo-horizontal-blanco.svg',
                          'logo-vertical.svg', 'isotipo.svg', 'favicon-32.png',
                          'apple-touch-icon-180.png', 'og-image-1200x630.png',
                          'concepts/concepto-1.svg', 'concepts/concepto-2.svg', 'concepts/concepto-3.svg']]
    page.write_text('<!doctype html><html lang="es"><meta charset="utf-8"><title>Pulso Energético · Revisión de exportaciones</title><style>'
                    'body{margin:0;padding:24px;background:#FFF1D9;font:14px system-ui;color:#06323B}'
                    'main{display:grid;grid-template-columns:1fr 1fr;gap:20px}'
                    'section{padding:16px;border:1px solid #455f60;min-width:0}'
                    'section:nth-child(2),section:nth-child(4){background:#06323B;color:#FFF1D9}'
                    'section:nth-child(5) img,section:nth-child(6) img{max-height:240px;width:auto!important}'
                    'section:nth-child(8) img{width:180px!important}img{display:block;max-width:100%}'
                    'h2{font-size:13px}</style><h1>Kit Pulso Energético</h1><main>' + ''.join(items) + '</main></html>')
    chrome('--window-size=1440,2040', '--virtual-time-budget=2000',
           '--screenshot=' + str(ROOT / 'preview-kit.png'), page.as_uri())
    shutil.rmtree(ROOT / '.chrome-profile')
    print('PASS: 5 PNG exports at exact requested sizes; manual screenshot + PDF; kit contact sheet.')

if __name__ == '__main__':
    main()
