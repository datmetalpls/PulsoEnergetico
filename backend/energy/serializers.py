from django.utils import timezone
from . import discord


def operable(user, site):
    return user.is_authenticated and site.operators.filter(id=user.id).exists()


def role(user):
    return 'operator' if user.is_authenticated and user.operable_sites.exists() else 'observer'


def discord_status(session):
    # Nunca incluye la URL del webhook: solo si existe y cuándo se envió.
    alert_sent = session.alerts.filter(discord_sent_at__isnull=False).order_by('-discord_sent_at').first()
    times = [t for t in [alert_sent.discord_sent_at if alert_sent else None, session.discord_report_sent_at] if t]
    last = max(times) if times else None
    is_configured = discord.configured()
    sent = alert_sent is not None or session.discord_report_sent_at is not None
    label = 'Enviado a Discord' if sent else ('Discord configurado' if is_configured else 'Simulación local')
    return {'configured': is_configured, 'last_sent_at': last.isoformat() if last else None,
            'alert_sent': alert_sent is not None, 'report_sent': session.discord_report_sent_at is not None,
            'sent': sent, 'label': label}


def state_json(session, user):
    site, locality = session.site, session.site.locality
    states = list(session.zone_states.select_related('zone').order_by('zone_id'))
    power = sum(s.power_w for s in states)
    remaining = max(session.threshold_wh - session.energy_wh, 0)
    seconds = (8 * 3600 + session.scenario_offset_s) % 86400
    band, band_label = ('day', 'Día') if 8 * 3600 <= seconds < 14 * 3600 else (
        ('afternoon', 'Tarde') if 14 * 3600 <= seconds < 19 * 3600 else ('night', 'Noche'))
    series, total_points = {}, {}
    for zs in states:
        readings = list(session.readings.filter(zone=zs.zone).exclude(flag='out_of_order').order_by('-t_s', '-id')[:600])
        series[zs.zone.slug] = [dict(t_s=r.t_s, power_w=r.power_w, energy_wh=r.energy_wh) for r in reversed(readings)]
    # Build total using every accepted sample, so truncated zone histories keep correct totals.
    latest = {s.zone_id: (0, 0) for s in states}
    for r in session.readings.exclude(flag='out_of_order').order_by('t_s', 'id').iterator():
        latest[r.zone_id] = (r.power_w, r.energy_wh)
        total_points[r.t_s] = {'t_s': r.t_s, 'power_w': sum(v[0] for v in latest.values()),
                              'energy_wh': sum(v[1] for v in latest.values())}
    series['total'] = list(total_points.values())[-600:]
    alerts = [{'id': str(a.id), 'kind': a.kind, 't_s': a.t_s, 'energy_wh': a.energy_wh,
        'threshold_wh': a.threshold_wh, 'channel': a.channel,
        'channel_label': 'Aviso del navegador (imita el buzzer)' if a.channel == 'browser' else 'Buzzer físico en Wokwi',
        'message': f'Se alcanzó el umbral de {a.threshold_wh:.4f} Wh'.replace('.', ','),
        'acknowledged': a.acknowledged_at is not None,
        'discord_sent_at': a.discord_sent_at.isoformat() if a.discord_sent_at else None} for a in session.alerts.order_by('id')]
    zones = []
    for s in states:
        z = s.zone
        enabled = s.power_w > 0
        label = ('Carga habilitada' if enabled else 'Carga deshabilitada') if z.kind == 'dc_load' else (
            'Encendida' if enabled else 'Apagada')
        zones.append({'slug': z.slug, 'name': z.name, 'kind': z.kind, 'dimmable': z.dimmable,
            'simulated_control': True, 'on': s.on, 'indicator': {'led': 'green' if enabled else 'off', 'label': label},
            'voltage_v': z.nominal_voltage_v, 'current_a': s.power_w / z.nominal_voltage_v,
            'setpoint_current_a': s.current_a if z.kind == 'dc_load' else None,
            'max_current_a': z.max_current_a, 'intensity_pct': s.intensity_pct if z.dimmable else None,
            'power_w': s.power_w, 'energy_wh': s.energy_wh, 'on_seconds': s.on_seconds})
    return {'contract_version': '0.1', 'data_label': 'Datos simulados', 'server_time': timezone.now().isoformat(),
        'locality': {k: getattr(locality, k) for k in ['slug', 'name', 'country', 'timezone']},
        'site': {k: getattr(site, k) for k in ['slug', 'name', 'kind', 'fictitious', 'budget_kwh_day', 'sample_interval_s']},
        'sources_available': ['simulator', 'wokwi_import'], 'active_source': session.active_source,
        'hardware': {'simulated_board': 'Raspberry Pi Pico (Wokwi)', 'planned_board': 'Raspberry Pi Zero W (montaje físico previsto)'},
        'permissions': {'role': role(user), 'can_operate': operable(user, site)},
        'session': {'id': str(session.id), 'status': session.status, 'started_at': session.started_at.isoformat(),
            'playing': session.playing, 'speed': session.speed, 'connected': session.connected,
            'elapsed_s': session.elapsed_s, 'scenario_clock': f'{seconds // 3600:02}:{seconds % 3600 // 60:02}:{seconds % 60:02}',
            'band': band, 'band_label': band_label, 'threshold_wh': session.threshold_wh, 'energy_wh': session.energy_wh,
            'remaining_wh': remaining, 'total_power_w': power, 'time_to_threshold_s': remaining * 3600 / power if power else None,
            'status_label': 'Presupuesto alcanzado' if session.alert_fired else ('Consumiendo' if power else 'Consumo detenido'),
            'alert_fired': session.alert_fired},
        'zones': zones, 'alerts': alerts, 'discord': discord_status(session),
        'gaps': [{'zone': g.zone.slug, 'from_t_s': g.from_t_s, 'to_t_s': g.to_t_s,
                  'duration_s': g.to_t_s - g.from_t_s, 'label': 'Sin datos: conexión interrumpida'}
                 for g in session.gaps.select_related('zone').order_by('id')],
        'series': series, 'context_card': None if site.kind == 'bench' else {
            'label': 'Estimación ilustrativa', 'unit': 'MWh/día',
            'text': 'Rangos urbanos aportados por el equipo: pendientes. El banco de pruebas mantiene su escala en Wh.'}}


def report_json(session):
    power = sum(session.zone_states.values_list('power_w', flat=True)) if session.status == 'running' else 0
    on_seconds = max(session.zone_states.values_list('on_seconds', flat=True), default=0)
    alert = session.alerts.order_by('t_s').first()
    status = discord_status(session)
    energy = f'{session.energy_wh:.4f}'.replace('.', ',')
    threshold = f'{session.threshold_wh:.4f}'.replace('.', ',')
    text = (f'Resumen del ensayo en {session.site.name}, {session.site.locality.name}. Datos simulados. '
            f'Energía acumulada: {energy} vatios hora. Umbral: {threshold} vatios hora. '
            f'Consumo efectivo: {on_seconds:g} segundos. ' +
            ('Se emitió una alerta de umbral. ' if alert else 'No se alcanzó el umbral. ') +
            f'Potencia actual: {power:g} vatios' + (', consumo detenido.' if power == 0 else '.'))
    return {'session_id': str(session.id), 'site': session.site.name, 'locality': session.site.locality.name,
        'data_label': 'Datos simulados', 'values': {'elapsed_s': session.elapsed_s, 'on_seconds': on_seconds,
            'energy_wh': session.energy_wh, 'threshold_wh': session.threshold_wh, 'power_w': power,
            'alert_fired': session.alert_fired, 'alert_t_s': alert.t_s if alert else None},
        'discord': {k: status[k] for k in ['configured', 'last_sent_at', 'alert_sent', 'report_sent']},
        'text': text, 'discord_preview': {'label': status['label'], 'sent': status['sent'],
            'content': f'⚡ Pulso Energético · {session.site.name} ({session.site.locality.name}) — '
                       f'Acumulado {energy} Wh, umbral {threshold} Wh en {on_seconds:g} s de consumo. [Datos simulados]'}}
