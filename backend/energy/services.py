import math
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .engine import integrate
from .models import Session, ZoneState, Reading, Gap, Alert, AuditEvent


def audit(user, session, action, payload=None):
    AuditEvent.objects.create(user=user, session=session, action=action, payload=payload or {})


def new_session(site, threshold=None):
    # Caller locks the site, serializing simultaneous session creation.
    for old in Session.objects.select_for_update().filter(site=site, status='running'):
        catch_up(old)
        old.status, old.playing, old.closed_at = 'closed', False, timezone.now()
        old.save()
    session = Session.objects.create(site=site, threshold_wh=threshold if threshold is not None else
                                     (0.02 if site.kind == 'bench' else site.budget_kwh_day * 1000),
                                     speed=site.default_speed)
    for zone in site.zones.all():
        ZoneState.objects.create(session=session, zone=zone)
    return session


def ingest(session, zone, reading_id, t_s, voltage_v, current_a, source='simulator', instant=None):
    if Reading.objects.filter(reading_id=reading_id).exists():
        return 'duplicate'
    state = ZoneState.objects.get(session=session, zone=zone)
    interval = integrate(state.last_t_s, state.power_w, t_s, session.site.sample_interval_s,
                         gap_pending=state.gap_pending)
    power = voltage_v * current_a
    if interval.flag != 'out_of_order':
        if interval.flag == 'gap_after' and state.last_t_s is not None:
            Gap.objects.create(session=session, zone=zone, from_t_s=state.last_t_s, to_t_s=t_s)
        state.energy_wh += interval.energy_wh
        state.on_seconds += interval.on_seconds
        state.last_t_s, state.power_w, state.gap_pending = t_s, power, False
        state.save()
        session.energy_wh = sum(session.zone_states.values_list('energy_wh', flat=True))
        if session.energy_wh >= session.threshold_wh - 1e-9 and not session.alert_fired:
            Alert.objects.get_or_create(session=session, kind='threshold', defaults={
                't_s': t_s, 'energy_wh': session.energy_wh, 'threshold_wh': session.threshold_wh,
                'channel': 'wokwi_buzzer' if source == 'wokwi_import' else 'browser'})
            session.alert_fired = True
        session.save()
    Reading.objects.create(reading_id=reading_id, session=session, zone=zone, t_s=t_s,
        instant=instant or session.started_at + timedelta(seconds=t_s), voltage_v=voltage_v,
        current_a=current_a, power_w=power, interval_wh=interval.energy_wh,
        energy_wh=state.energy_wh, flag=interval.flag, source=source)
    return interval.flag


def simulated_power(state):
    zone = state.zone
    return (zone.nominal_voltage_v * state.current_a if zone.kind == 'dc_load' else
            zone.nominal_power_w * (state.intensity_pct / 100 if zone.dimmable else 1)) if state.on else 0


def emit(session, state, suffix=''):
    zone = state.zone
    session.active_source = 'simulator'
    power = simulated_power(state)
    return ingest(session, zone, f'{session.id}:{zone.slug}:{session.elapsed_s}{suffix}',
                  session.elapsed_s, zone.nominal_voltage_v, power / zone.nominal_voltage_v)


def immediate(session):
    if not session.connected:
        return
    # Mutation suffix distinguishes same-time state changes from scheduled samples.
    suffix = f':change:{session.readings.count()}'
    for state in session.zone_states.select_related('zone').all():
        emit(session, state, suffix)


def advance(session, seconds):
    start, end = session.elapsed_s, session.elapsed_s + seconds
    interval = session.site.sample_interval_s
    if session.connected:
        states = list(session.zone_states.select_related('zone').order_by('zone_id'))
        points = range((start // interval + 1) * interval, end + 1, interval)
        # Exact /advance durations include a final partial sample.
        times = [start, *points]
        if times[-1] != end:
            times.append(end)
        readings, gaps = [], []
        for t_s in times:
            for state in states:
                if t_s == start and state.last_t_s is not None:
                    continue
                zone = state.zone
                result = integrate(state.last_t_s, state.power_w, t_s, interval, gap_pending=state.gap_pending)
                if result.flag == 'gap_after' and state.last_t_s is not None:
                    gaps.append(Gap(session=session, zone=zone, from_t_s=state.last_t_s, to_t_s=t_s))
                power = simulated_power(state)
                state.energy_wh += result.energy_wh
                state.on_seconds += result.on_seconds
                state.last_t_s, state.power_w, state.gap_pending = t_s, power, False
                session.energy_wh = sum(s.energy_wh for s in states)
                if session.energy_wh >= session.threshold_wh - 1e-9 and not session.alert_fired:
                    Alert.objects.get_or_create(session=session, kind='threshold', defaults={
                        't_s': t_s, 'energy_wh': session.energy_wh, 'threshold_wh': session.threshold_wh})
                    session.alert_fired = True
                readings.append(Reading(reading_id=f'{session.id}:{zone.slug}:{t_s}', session=session,
                    zone=zone, t_s=t_s, instant=session.started_at + timedelta(seconds=t_s),
                    voltage_v=zone.nominal_voltage_v, current_a=power / zone.nominal_voltage_v,
                    power_w=power, interval_wh=result.energy_wh, energy_wh=state.energy_wh,
                    flag=result.flag, source='simulator'))
        Reading.objects.bulk_create(readings, batch_size=1000)
        Gap.objects.bulk_create(gaps)
        ZoneState.objects.bulk_update(states, ['energy_wh', 'on_seconds', 'last_t_s', 'power_w', 'gap_pending'])
        session.active_source = 'simulator'
    session.elapsed_s = end
    session.scenario_offset_s += seconds
    session.save()


def catch_up(session):
    if not session.playing or session.status != 'running':
        return
    now = timezone.now()
    ticks = max(0, math.floor((now - session.last_tick_wall).total_seconds()))
    if not ticks:
        return
    # Bound work per request without discarding time or inventing a connection gap.
    processed = min(ticks, 3600)
    advance(session, processed * session.speed)
    session.last_tick_wall += timedelta(seconds=processed)
    session.save()


def next_band(session):
    clock = (8 * 3600 + session.scenario_offset_s) % 86400
    next_start = next((s for s in [8 * 3600, 14 * 3600, 19 * 3600] if s > clock), 32 * 3600)
    session.scenario_offset_s += next_start - clock
    session.save()


def comparison(site, duration, meeting_end):
    runs = []
    for key, label, end in [('A', 'Sala encendida', duration),
                             ('B', 'Sala apagada al terminar la reunión', meeting_end)]:
        zones = []
        for zone in site.zones.all():
            seconds = duration if zone.slug == 'salon-principal' else end
            value = integrate(0, zone.nominal_power_w, seconds, max(1, duration)).energy_wh
            zones.append({'zone': zone.slug, 'energy_wh': value, 'on_seconds': seconds})
        runs.append({'key': key, 'label': label, 'energy_wh': sum(z['energy_wh'] for z in zones), 'zones': zones})
    return {'duration_s': duration, 'runs': runs, 'difference_wh': runs[0]['energy_wh'] - runs[1]['energy_wh'],
            'salon_on_seconds': duration, 'note': 'Datos de demostración'}
