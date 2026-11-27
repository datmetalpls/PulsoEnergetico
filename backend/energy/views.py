import json
import math
import time
from pathlib import Path
from functools import wraps
from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse, FileResponse, Http404
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import Locality, Site, Session, ZoneState, Reading, Alert
from .serializers import state_json, report_json, role, operable
from .services import audit, new_session, catch_up, advance, immediate, next_band, ingest, comparison


class APIError(Exception):
    def __init__(self, error, status=400, fields=None, headers=None):
        self.error, self.status, self.fields, self.headers = error, status, fields, headers or {}


def invalid(field, message='Valor inválido'):
    raise APIError('validation', fields={field: message})


def number(value, low, high, field, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        invalid(field)
    if not low <= value <= high or not math.isfinite(value) or (integer and int(value) != value):
        invalid(field)
    return int(value) if integer else value


def boolean(value, field):
    if type(value) is not bool:
        invalid(field)
    return value


def fields_only(data, allowed):
    for key in data.keys() - set(allowed):
        invalid(key, 'Campo no admitido')


def endpoint(methods):
    def decorate(fn):
        @wraps(fn)
        def wrapped(request, **kwargs):
            if request.method not in methods:
                return JsonResponse({'error': 'method_not_allowed'}, status=405)
            try:
                data = {}
                if request.method != 'GET':
                    try:
                        body = request.body
                        data = json.loads(body) if body else {}
                    except RequestDataTooBig:
                        invalid('body', 'El cuerpo supera el límite de 2 MiB')
                    except (ValueError, UnicodeError, RecursionError):
                        invalid('body', 'JSON inválido')
                    if not isinstance(data, dict):
                        invalid('body')
                with transaction.atomic():
                    return fn(request, data=data, **kwargs)
            except APIError as exc:
                body = {'error': exc.error}
                if exc.fields is not None:
                    body['fields'] = exc.fields
                response = JsonResponse(body, status=exc.status)
                for key, value in exc.headers.items():
                    response[key] = value
                return response
            except (Site.DoesNotExist, Session.DoesNotExist, ZoneState.DoesNotExist, Alert.DoesNotExist):
                return JsonResponse({'error': 'not_found'}, status=404)
        return wrapped
    return decorate


def require_user(request):
    if not request.user.is_authenticated:
        raise APIError('forbidden', 403)


def require_operator(request, site):
    require_user(request)
    if not operable(request.user, site):
        raise APIError('forbidden', 403)


def locked_session(request, session_id, write=False):
    session = Session.objects.select_for_update().get(id=session_id)
    if write:
        require_operator(request, session.site)
        if session.status == 'closed':
            raise APIError('session_closed', 409)
    else:
        require_user(request)
    catch_up(session)
    return session


def login_rate_key(request):
    return f"login_fail:{request.META.get('REMOTE_ADDR', 'unknown')}"


def login_recent_failures(key, now, window):
    return [ts for ts in cache.get(key, []) if now - ts < window]


def csrf_failure(request, reason=''):
    return JsonResponse({'error': 'forbidden'}, status=403)


@endpoint(['GET', 'POST'])
def auth(request, action, data):
    if action in ['csrf', 'me'] and request.method != 'GET':
        raise APIError('method_not_allowed', 405)
    if action in ['login', 'logout'] and request.method != 'POST':
        raise APIError('method_not_allowed', 405)
    if action == 'csrf':
        get_token(request)
        return JsonResponse({'status': 'ok'})
    if action == 'login':
        fields_only(data, ['username', 'password'])
        if not isinstance(data.get('username'), str) or not isinstance(data.get('password'), str):
            invalid('credentials')
        limit = getattr(settings, 'LOGIN_RATE_LIMIT', 5)
        window = getattr(settings, 'LOGIN_RATE_WINDOW_S', 60)
        rate_key = login_rate_key(request)
        now = time.time()
        recent = login_recent_failures(rate_key, now, window)
        if len(recent) >= limit:
            retry_after = max(1, math.ceil(window - (now - recent[0])))
            raise APIError('rate_limited', 429, headers={'Retry-After': str(retry_after)})
        user = authenticate(request, username=data['username'], password=data['password'])
        if not user:
            recent.append(now)
            cache.set(rate_key, recent, timeout=window)
            raise APIError('forbidden', 403)
        cache.delete(rate_key)
        login(request, user)
        audit(user, None, 'auth.login')
    elif action == 'logout':
        audit(request.user if request.user.is_authenticated else None, None, 'auth.logout')
        logout(request)
    return JsonResponse({'authenticated': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else '', 'role': role(request.user),
        'operable_sites': list(request.user.operable_sites.values_list('slug', flat=True)) if request.user.is_authenticated else []})


@endpoint(['GET'])
def localities(request, data):
    require_user(request)
    return JsonResponse([{**{k: getattr(loc, k) for k in ['slug', 'name', 'country', 'timezone']},
        'sites': [{k: getattr(s, k) for k in ['slug', 'name', 'kind', 'fictitious', 'budget_kwh_day', 'sample_interval_s']}
                  for s in loc.sites.order_by('id')]}
        for loc in Locality.objects.order_by('id')], safe=False)


@endpoint(['GET', 'PATCH', 'POST'])
def site_endpoint(request, slug, action=None, data=None):
    site = Site.objects.select_for_update().get(slug=slug)
    if action == 'comparison' and request.method == 'GET':
        require_user(request)
        if site.kind != 'venue':
            invalid('site', 'Solo sedes')
        try:
            duration = int(request.GET.get('duration_s', 21600))
            end = int(request.GET.get('meeting_end_s', 10800))
        except (ValueError, TypeError):
            invalid('duration_s')
        number(duration, 1, 86400, 'duration_s', True)
        number(end, 0, duration, 'meeting_end_s', True)
        return JsonResponse(comparison(site, duration, end))
    if action == 'sessions' and request.method == 'POST':
        require_operator(request, site)
        fields_only(data, ['threshold_wh'])
        threshold = data.get('threshold_wh')
        if threshold is not None:
            if site.kind != 'bench':
                invalid('threshold_wh', 'Solo banco')
            number(threshold, .001, 10, 'threshold_wh')
        session = new_session(site, threshold)
        audit(request.user, session, 'sessions.create', data)
    elif action == 'state' and request.method == 'GET':
        require_user(request)
        session = Session.objects.select_for_update().get(site=site, status='running')
        catch_up(session)
    elif action is None and request.method == 'PATCH':
        require_operator(request, site)
        fields_only(data, ['budget_kwh_day'])
        if site.kind != 'venue':
            invalid('budget_kwh_day', 'Solo sedes')
        budget = number(data.get('budget_kwh_day'), .05, 50, 'budget_kwh_day')
        session = Session.objects.select_for_update().get(site=site, status='running')
        catch_up(session)
        site.budget_kwh_day = budget
        site.save()
        session.threshold_wh = budget * 1000
        session.site = site
        session.save()
        immediate(session)
        audit(request.user, session, 'site.budget', data)
    else:
        raise APIError('method_not_allowed', 405)
    return JsonResponse(state_json(session, request.user))


def import_readings(session, data):
    fields_only(data, ['source', 'readings', 'expected'])
    source = data.get('source')
    if source not in ['wokwi_import', 'device']:
        invalid('source')
    rows = data.get('readings')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 5000:
        invalid('readings')
    parsed = []
    for row in rows:
        if not isinstance(row, dict):
            invalid('readings')
        fields_only(row, ['reading_id', 'zone', 'instant', 'voltage_v', 'current_a', '_comment'])
        rid = row.get('reading_id')
        if not isinstance(rid, str) or not 1 <= len(rid) <= 200 or '\x00' in rid:
            invalid('reading_id')
        try:
            zone = session.site.zones.get(slug=row.get('zone'))
        except (TypeError, ValueError, session.site.zones.model.DoesNotExist):
            invalid('zone')
        raw_instant = row.get('instant')
        try:
            instant = parse_datetime(raw_instant) if isinstance(raw_instant, str) else None
        except ValueError:
            instant = None
        if instant is None or timezone.is_naive(instant):
            invalid('instant', 'Fecha ISO 8601 con zona horaria requerida')
        voltage = number(row.get('voltage_v'), 0, zone.nominal_voltage_v, 'voltage_v')
        limit = zone.max_current_a if zone.max_current_a is not None else zone.nominal_power_w / zone.nominal_voltage_v
        current = number(row.get('current_a'), 0, limit, 'current_a')
        existing = Reading.objects.filter(reading_id=rid).first()
        if existing and (existing.session_id != session.id or existing.zone_id != zone.id):
            invalid('reading_id', 'Identificador perteneciente a otra sesión o zona')
        parsed.append((zone, rid, instant, voltage, current))
    origin = session.telemetry_origin or parsed[0][2]
    # Both session clocks are PostgreSQL positive integers (up to 2**31 - 1).
    max_t = session.elapsed_s + min(2**31 - 1 - session.elapsed_s, 2**31 - 1 - session.scenario_offset_s)
    for _, _, instant, _, _ in parsed:
        number((instant - origin).total_seconds(), -(2**31 - 1), max_t, 'instant')
    session.telemetry_origin = origin
    outcomes = []
    for zone, rid, instant, voltage, current in parsed:
        t_s = (instant - session.telemetry_origin).total_seconds()
        result = ingest(session, zone, rid, t_s, voltage, current, source, instant)
        outcomes.append(result)
        if result not in ['out_of_order', 'duplicate']:
            zs = ZoneState.objects.get(session=session, zone=zone)
            zs.on = current > 0
            if zone.kind == 'dc_load':
                zs.current_a = current
            elif zone.dimmable:
                zs.intensity_pct = voltage * current / zone.nominal_power_w * 100
            zs.save()
            if t_s > session.elapsed_s:
                delta = math.ceil(t_s) - session.elapsed_s
                session.elapsed_s += delta
                session.scenario_offset_s += delta
    session.active_source, session.playing = source, False
    session.save()
    return outcomes


@endpoint(['POST', 'GET'])
def session_endpoint(request, session_id, action, data, zone_slug=None, alert_id=None):
    if action not in ['play', 'pause', 'next-band', 'advance', 'speed', 'connection', 'readings', 'report', 'zones', 'ack']:
        raise APIError('not_found', 404)
    if action == 'report' and request.method == 'GET':
        session = locked_session(request, session_id)
        return JsonResponse(report_json(session))
    if request.method != 'POST' or action == 'report':
        raise APIError('method_not_allowed', 405)
    session = locked_session(request, session_id, True)
    allowed = {'play': [], 'pause': [], 'next-band': [], 'advance': ['seconds'], 'speed': ['speed'],
               'connection': ['connected'], 'zones': ['on', 'current_a', 'intensity_pct'], 'ack': [],
               'readings': ['source', 'readings', 'expected']}
    fields_only(data, allowed[action])
    status = 200
    if action in ['play', 'pause']:
        session.playing = action == 'play'
        session.last_tick_wall = timezone.now()
        immediate(session)
        session.save()
    elif action == 'advance':
        seconds = number(data.get('seconds'), 1, 3600, 'seconds', True)
        advance(session, seconds)
    elif action == 'next-band':
        next_band(session)
    elif action == 'speed':
        speed = number(data.get('speed'), 1, 300, 'speed', True)
        if speed not in ([1] if session.site.kind == 'bench' else [60, 300]):
            invalid('speed')
        session.speed = speed
        session.last_tick_wall = timezone.now()
        session.save()
    elif action == 'connection':
        connected = boolean(data.get('connected'), 'connected')
        if not connected:
            immediate(session)
            session.zone_states.update(gap_pending=True)
        session.connected = connected
        session.save()
        if connected:
            immediate(session)
    elif action == 'zones':
        zs = ZoneState.objects.select_related('zone').get(session=session, zone__slug=zone_slug)
        if not data:
            invalid('body')
        if 'on' in data:
            zs.on = boolean(data['on'], 'on')
        if 'current_a' in data:
            if zs.zone.kind != 'dc_load':
                invalid('current_a')
            zs.current_a = number(data['current_a'], 0, zs.zone.max_current_a, 'current_a')
            if abs(zs.current_a * 100 - round(zs.current_a * 100)) > 1e-9:
                invalid('current_a', 'Paso de 0,01 A requerido')
        if 'intensity_pct' in data:
            if not zs.zone.dimmable:
                invalid('intensity_pct')
            zs.intensity_pct = number(data['intensity_pct'], 0, 100, 'intensity_pct')
        zs.save()
        immediate(session)
    elif action == 'ack':
        alert = Alert.objects.get(session=session, id=alert_id)
        if alert.acknowledged_at is None:
            alert.acknowledged_at = timezone.now()
            alert.save()
    elif action == 'readings':
        outcomes = import_readings(session, data)
        if all(o == 'duplicate' for o in outcomes):
            audit(request.user, session, action, {'source': data.get('source'), 'count': len(outcomes)})
            return JsonResponse({'status': 'duplicate'})
        if any(o == 'out_of_order' for o in outcomes):
            status = 202
    audit(request.user, session, action, {'source': data.get('source'), 'count': len(data['readings'])}
          if action == 'readings' else data)
    return JsonResponse(state_json(session, request.user), status=status)


def spa(request, path=''):
    if path.split('/')[0] in ['api', 'admin', 'static']:
        raise Http404
    index = Path(settings.WHITENOISE_ROOT) / 'index.html'
    if not index.is_file():
        raise Http404('Angular build missing')
    return FileResponse(index.open('rb'), content_type='text/html')


def api_missing(request, path=''):
    return JsonResponse({'error': 'not_found'}, status=404)
