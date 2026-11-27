"""Envío opcional a Discord mediante webhook (sin bot ni dependencias nuevas).

La URL del webhook es un secreto: se lee de DISCORD_WEBHOOK_URL y nunca se
registra, se serializa ni se incluye en mensajes de error.
"""
import json
import logging
import os
import sys
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger(__name__)

USERNAME = 'Pulso Energético'
FOOTER = 'Datos simulados · Prototipo hackatón Ecuador × Chile'
COLOR_PETROLEO = 0x0F4C5C
COLOR_DORADO = 0xC9A227
TIMEOUT_S = 5
_TESTING = sys.argv[1:2] == ['test']


@dataclass
class Result:
    ok: bool
    status: int | None = None
    retry_after: int | None = None


def webhook_url():
    # Las pruebas nunca usan el webhook real del entorno; lo inyectan con patch.
    if _TESTING:
        return os.environ.get('DISCORD_WEBHOOK_URL_TEST', '').strip()
    return os.environ.get('DISCORD_WEBHOOK_URL', '').strip()


def configured():
    return bool(webhook_url())


def send(payload):
    """Publica payload en el webhook. Nunca lanza excepciones ni reintenta."""
    url = webhook_url()
    if not url:
        return Result(False)
    body = {'username': USERNAME, 'allowed_mentions': {'parse': []}, **payload}
    avatar = os.environ.get('DISCORD_AVATAR_URL', '').strip()
    if avatar:
        body.setdefault('avatar_url', avatar)
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method='POST',
                                     headers={'Content-Type': 'application/json',
                                              'User-Agent': 'PulsoEnergetico (prototipo, 0.1)'})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            status = response.status
        return Result(200 <= status < 300, status)
    except urllib.error.HTTPError as exc:
        retry = None
        if exc.code == 429:
            try:
                retry = max(1, round(float(exc.headers.get('Retry-After') or 0) + .5))
            except (TypeError, ValueError):
                retry = 30
        # Solo el código HTTP: la URL del webhook es secreta.
        logger.warning('Discord respondió HTTP %s', exc.code)
        return Result(False, exc.code, retry)
    except Exception as exc:  # timeout, DNS, TLS…
        logger.warning('Discord no disponible (%s)', type(exc).__name__)
        return Result(False)


def run_async(fn):
    """Ejecuta fn fuera del ciclo de la petición; en pruebas, en línea."""
    if _TESTING:
        fn()
        return

    def target():
        from django.db import connection
        try:
            fn()
        finally:
            connection.close()
    threading.Thread(target=target, daemon=True).start()


def fmt(value, decimals):
    return f'{value:.{decimals}f}'.replace('.', ',')


def energy_text(site, wh):
    return f'{fmt(wh, 4)} Wh' if site.kind == 'bench' else f'{fmt(wh / 1000, 2)} kWh'


def alert_payload(alert, scenario_clock):
    session = alert.session
    site = session.site
    return {'embeds': [{
        'title': 'Alerta de umbral alcanzado',
        'description': f'{site.name} ({site.locality.name}) alcanzó el umbral configurado.',
        'color': COLOR_DORADO,
        'fields': [
            {'name': 'Sitio', 'value': site.name, 'inline': True},
            {'name': 'Localidad', 'value': f'{site.locality.name}, {site.locality.country}', 'inline': True},
            {'name': 'Hora del escenario', 'value': scenario_clock, 'inline': True},
            {'name': 'Energía acumulada', 'value': energy_text(site, alert.energy_wh), 'inline': True},
            {'name': 'Umbral', 'value': energy_text(site, alert.threshold_wh), 'inline': True},
        ],
        'footer': {'text': FOOTER},
    }]}


def report_payload(session, report):
    site = session.site
    values = report['values']
    return {'embeds': [{
        'title': f'Reporte del ensayo · {site.name}',
        'description': report['text'][:4000],
        'color': COLOR_PETROLEO,
        'fields': [
            {'name': 'Localidad', 'value': f'{site.locality.name}, {site.locality.country}', 'inline': True},
            {'name': 'Energía acumulada', 'value': energy_text(site, values['energy_wh']), 'inline': True},
            {'name': 'Umbral', 'value': energy_text(site, values['threshold_wh']), 'inline': True},
        ],
        'footer': {'text': FOOTER},
    }]}
