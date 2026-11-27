import io
import json
import os
from datetime import timedelta
from pathlib import Path
from time import perf_counter
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.db import transaction, IntegrityError, connection
from django.test import TestCase, Client
from django.utils import timezone
from .models import Site, Session, ZoneState, Reading, Alert, Gap, AuditEvent, Locality, Zone
from .engine import integrate
from .services import ingest, catch_up


class DemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)

    def setUp(self):
        self.client.force_login(get_user_model().objects.get(username='operador_cuenca'))
        self.site = Site.objects.get(slug='cuenca-banco')
        self.session = Session.objects.get(site=self.site, status='running')
        self.base = f'/api/sessions/{self.session.id}'

    def post(self, action, body=None, base=None, expected=200):
        response = self.client.post((base or self.base) + '/' + action, json.dumps(body or {}), content_type='application/json')
        self.assertEqual(response.status_code, expected, response.content[:1000])
        return response.json()

    def state(self, slug='cuenca-banco', client=None):
        response = (client or self.client).get(f'/api/sites/{slug}/state')
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_postgres_and_seed_idempotent(self):
        self.assertEqual(connection.vendor, 'postgresql')
        counts = [m.objects.count() for m in [Locality, Site, Zone, Session, ZoneState, get_user_model()]]
        call_command('seed_demo', verbosity=0)
        call_command('seed_demo', verbosity=0)
        self.assertEqual(counts, [m.objects.count() for m in [Locality, Site, Zone, Session, ZoneState, get_user_model()]])

    def test_acceptance_and_refresh_and_single_alert(self):
        result = self.post('zones/carga-5v', {'on': True, 'current_a': .4})
        self.assertEqual(result['zones'][0]['power_w'], 2)
        result = self.post('advance', {'seconds': 18})
        self.assertAlmostEqual(result['session']['energy_wh'], .01, places=9)
        self.post('zones/carga-5v', {'on': False})
        result = self.post('advance', {'seconds': 10})
        self.assertAlmostEqual(result['session']['energy_wh'], .01, places=9)
        self.post('zones/carga-5v', {'on': True})
        result = self.post('advance', {'seconds': 18})
        self.assertAlmostEqual(result['session']['energy_wh'], .02, places=9)
        self.assertEqual(len(result['alerts']), 1)
        self.post('zones/carga-5v', {'on': False})
        self.post('zones/carga-5v', {'on': True})
        self.post('advance', {'seconds': 1})
        self.assertEqual(Alert.objects.filter(session=self.session).count(), 1)
        second = Client()
        second.force_login(get_user_model().objects.get(username='observador'))
        self.assertEqual(self.state()['session'], self.state(client=second)['session'])
        self.assertTrue(AuditEvent.objects.filter(session=self.session, action='advance').exists())

    def test_next_band_no_energy_no_elapsed(self):
        self.post('zones/carga-5v', {'on': True})
        before = self.post('advance', {'seconds': 18})
        after = self.post('next-band')
        for field in ['elapsed_s', 'energy_wh']:
            self.assertEqual(after['session'][field], before['session'][field])
        self.assertEqual(after['session']['scenario_clock'], '14:00:00')

    def test_fixture_duplicate_and_out_of_order(self):
        fixture = json.loads((settings.BASE_DIR.parent / 'contracts/telemetry.example.json').read_text())
        self.post('readings', fixture)
        self.assertEqual(Reading.objects.filter(session=self.session).count(), fixture['expected']['accepted'])
        self.assertAlmostEqual(self.state()['session']['energy_wh'], fixture['expected']['energy_wh'], places=6)
        energy = self.state()['session']['energy_wh']
        self.assertEqual(self.post('readings', fixture), {'status': 'duplicate'})
        self.assertEqual(self.state()['session']['energy_wh'], energy)
        self.assertEqual(self.post('play')['active_source'], 'simulator')
        self.assertFalse(Alert.objects.filter(session=self.session).exists())
        row = dict(fixture['readings'][0], reading_id='late')
        self.post('readings', {'source': 'device', 'readings': [row]}, expected=202)
        self.assertEqual(Reading.objects.get(reading_id='late').flag, 'out_of_order')
        self.assertEqual(self.state()['session']['energy_wh'], energy)

    def test_pure_engine_and_gap(self):
        self.assertEqual(integrate(None, 2, 0, 1).energy_wh, 0)
        self.assertEqual(integrate(10, 2, 9, 1).flag, 'out_of_order')
        self.assertEqual(integrate(0, 2, 4, 1).flag, 'gap_after')
        self.assertEqual(integrate(0, 2, 3, 1).energy_wh, 6 / 3600)
        self.post('zones/carga-5v', {'on': True})
        before = self.post('advance', {'seconds': 18})
        self.post('connection', {'connected': False})
        self.post('advance', {'seconds': 10})
        result = self.post('connection', {'connected': True})
        self.assertEqual(result['session']['energy_wh'], before['session']['energy_wh'])
        self.assertEqual(result['gaps'][0]['duration_s'], 10)
        self.assertEqual(result['session']['elapsed_s'], 28)
        self.post('advance', {'seconds': 1})
        self.assertAlmostEqual(self.state()['session']['energy_wh'], .01 + 2 / 3600, places=9)

    def test_short_disconnect_is_still_gap(self):
        self.post('zones/carga-5v', {'on': True})
        self.post('connection', {'connected': False})
        self.post('advance', {'seconds': 1})
        result = self.post('connection', {'connected': True})
        self.assertEqual(result['session']['energy_wh'], 0)
        self.assertEqual(result['gaps'][0]['duration_s'], 1)

    def test_permissions_csrf_and_auth(self):
        self.assertEqual(self.client.post('/api/sites/puente-alto-banco/sessions', '{}', content_type='application/json').status_code, 403)
        self.client.force_login(get_user_model().objects.get(username='observador'))
        self.post('advance', {'seconds': 1}, expected=403)
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/api/auth/login', '{}', content_type='application/json').status_code, 403)
        client.get('/api/auth/csrf')
        import os
        login = client.post('/api/auth/login', json.dumps({'username': 'operador_cuenca',
             'password': os.environ['DEMO_CUENCA_PASSWORD']}), content_type='application/json',
             HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(login.status_code, 200)
        self.assertEqual(client.post(self.base + '/advance', '{"seconds":1}', content_type='application/json').status_code, 403)
        self.assertEqual(client.post(self.base + '/advance', '{"seconds":1}', content_type='application/json',
             HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value).status_code, 200)
        self.assertEqual(client.get('/api/auth/me').json()['role'], 'operator')
        self.assertEqual(client.get('/api/localities').status_code, 200)
        localities = client.get('/api/localities').json()
        self.assertEqual(len(localities), 2)
        self.assertEqual(len(localities[0]['sites']), 2)
        self.assertIn('sample_interval_s', localities[0]['sites'][0])

    def test_independent_venues_both_directions(self):
        for own, other, username in [('cuenca-sede', 'puente-alto-sede', 'operador_cuenca'),
                                     ('puente-alto-sede', 'cuenca-sede', 'operador_puente')]:
            self.client.force_login(get_user_model().objects.get(username=username))
            session = Session.objects.get(site__slug=own, status='running')
            base = f'/api/sessions/{session.id}'
            untouched = self.state(other)['session']
            self.post('zones/salon-principal', {'on': True}, base)
            self.post('zones/sala-reuniones', {'on': True, 'intensity_pct': 75}, base)
            self.post('advance', {'seconds': 120}, base)
            before = self.state(own)
            self.post('zones/sala-reuniones', {'on': False}, base)
            self.post('advance', {'seconds': 120}, base)
            after = self.state(own)
            b = {z['slug']: z for z in before['zones']}
            a = {z['slug']: z for z in after['zones']}
            self.assertEqual(a['sala-reuniones']['power_w'], 0)
            self.assertEqual(a['sala-reuniones']['energy_wh'], b['sala-reuniones']['energy_wh'])
            self.assertGreater(a['salon-principal']['energy_wh'], b['salon-principal']['energy_wh'])
            self.assertEqual(self.state(other)['session'], untouched)

    def test_report_closing_values_and_comparison(self):
        self.post('zones/carga-5v', {'on': True})
        result = self.post('advance', {'seconds': 36})
        self.post('zones/carga-5v', {'on': False})
        self.client.post('/api/sites/cuenca-banco/sessions', '{}', content_type='application/json')
        report = self.client.get(self.base + '/report').json()
        self.assertAlmostEqual(report['values']['energy_wh'], result['session']['energy_wh'])
        self.assertEqual(report['values']['on_seconds'], 36)
        self.assertEqual(report['values']['power_w'], 0)
        self.assertEqual(report['discord_preview']['label'], 'Simulación local')
        self.assertFalse(report['discord_preview']['sent'])
        self.post('advance', {'seconds': 1}, expected=409)
        result = self.client.get('/api/sites/cuenca-sede/comparison').json()
        self.assertAlmostEqual(result['difference_wh'], 80 * (21600 - 10800) / 3600)
        self.assertEqual(result['salon_on_seconds'], 21600)
        self.assertEqual(result['runs'][0]['zones'][0]['on_seconds'], result['runs'][1]['zones'][0]['on_seconds'])

    def test_catch_up_lock_idempotency_after_hidden_tab(self):
        self.post('zones/carga-5v', {'on': True})
        self.session.refresh_from_db()
        now = timezone.now()
        self.session.playing, self.session.last_tick_wall = True, now - timedelta(seconds=600)
        self.session.save()
        with patch('energy.services.timezone.now', return_value=now):
            with transaction.atomic():
                session = Session.objects.select_for_update().get(id=self.session.id)
                catch_up(session)
            with transaction.atomic():
                again = Session.objects.select_for_update().get(id=self.session.id)
                catch_up(again)
        self.assertEqual(again.elapsed_s, 600)
        self.assertAlmostEqual(again.energy_wh, 2 * 600 / 3600)
        self.assertFalse(again.gaps.exists())
        self.assertEqual(again.alerts.get().t_s, 36)
        self.assertEqual(again.readings.count(), session.readings.count())

    def test_catch_up_keeps_backlog_after_one_hour(self):
        self.post('zones/carga-5v', {'on': True})
        self.session.refresh_from_db()
        now = timezone.now()
        self.session.playing, self.session.last_tick_wall = True, now - timedelta(seconds=3601)
        self.session.save()
        with patch('energy.services.timezone.now', return_value=now):
            catch_up(self.session)
            self.assertEqual(self.session.elapsed_s, 3600)
            self.assertEqual(self.session.last_tick_wall, now - timedelta(seconds=1))
            catch_up(self.session)
        self.assertEqual(self.session.elapsed_s, 3601)
        self.assertAlmostEqual(self.session.energy_wh, 2 * 3601 / 3600)
        self.assertFalse(self.session.gaps.exists())

    def test_ten_minute_hidden_tab_response_time(self):
        for slug, power in [('cuenca-banco', 2), ('cuenca-sede', 240)]:
            session = Session.objects.get(site__slug=slug, status='running')
            base = f'/api/sessions/{session.id}'
            for zone in session.site.zones.all():
                self.post('zones/' + zone.slug, {'on': True}, base)
            session.refresh_from_db()
            now = timezone.now()
            session.playing, session.last_tick_wall = True, now - timedelta(seconds=600)
            session.save()
            started = perf_counter()
            with patch('energy.services.timezone.now', return_value=now):
                state = self.state(slug)
            duration = perf_counter() - started
            print(f'Catch-up 10 min {slug}: {duration:.3f}s, {state["session"]["energy_wh"]:.6f} Wh')
            self.assertAlmostEqual(state['session']['energy_wh'], power * 600 * session.speed / 3600)
            self.assertEqual(state['gaps'], [])
            self.assertTrue(state['session']['playing'])
            self.assertLess(duration, 5, 'Catch-up blocks the demo for more than 5 seconds')

    def test_validation_prevents_overflow_nul_and_far_dates(self):
        self.post('advance', {'seconds': 10**400}, expected=400)
        row = dict(reading_id='security-probe', zone='carga-5v', instant='2026-11-27T00:00:00Z',
                   voltage_v=5, current_a=.4)
        for rows in [[dict(row, reading_id='security\x00nul')],
                     [row, dict(row, reading_id='future', instant='9999-01-01T00:00:00Z')]]:
            result = self.post('readings', {'source': 'device', 'readings': rows}, expected=400)
            self.assertEqual(result['error'], 'validation')
        self.session.refresh_from_db()
        self.assertEqual(self.session.elapsed_s, 0)
        self.assertIsNone(self.session.telemetry_origin)
        self.assertEqual(self.session.readings.count(), 0)

    def test_body_errors_are_json_and_max_batch_fits(self):
        for raw in ['{', '[0]', b'\xff', '{"seconds":' + '[' * 12000 + '0' + ']' * 12000 + '}',
                    ' ' * (settings.DATA_UPLOAD_MAX_MEMORY_SIZE + 1)]:
            response = self.client.post(self.base + '/advance', raw, content_type='application/json')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response['Content-Type'], 'application/json')
            self.assertEqual(response.json()['error'], 'validation')
        row = dict(reading_id='r' * 200, zone='carga-5v', instant='2026-11-27T00:00:00Z',
                   voltage_v=5, current_a=.4)
        body = {'source': 'device', 'readings': [row] * 5000}
        self.assertGreater(len(json.dumps(body)), 1048576)
        self.assertLess(len(json.dumps(body)), settings.DATA_UPLOAD_MAX_MEMORY_SIZE)
        self.post('readings', body)
        self.assertEqual(self.session.readings.count(), 1)
        self.post('readings', {'source': 'device', 'readings': [row] * 5001}, expected=400)

    def test_closed_session_report_has_no_current_power(self):
        self.post('zones/carga-5v', {'on': True})
        before = self.post('advance', {'seconds': 5})
        created = self.client.post('/api/sites/cuenca-banco/sessions', '{}', content_type='application/json')
        self.assertEqual(created.status_code, 200)
        report = self.client.get(self.base + '/report').json()
        self.assertEqual(report['values']['power_w'], 0)
        self.assertEqual(report['values']['energy_wh'], before['session']['energy_wh'])
        self.assertIn('Potencia actual: 0 vatios', report['text'])

    def test_validation_transaction_and_unique_alert(self):
        for action, body in [('zones/carga-5v', {'current_a': .81}), ('advance', {'seconds': True}),
                             ('advance', {'seconds': 1.5}), ('speed', {'speed': 300}),
                             ('connection', {'connected': 1}), ('zones/carga-5v', {'intensity_pct': 50}),
                             ('zones/carga-5v', {'current_a': .401}), ('advance', {'seconds': float('nan')})]:
            self.post(action, body, expected=400)
        self.assertEqual(self.state()['session']['elapsed_s'], 0)
        Alert.objects.create(session=self.session, t_s=0, energy_wh=.02, threshold_wh=.02)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Alert.objects.create(session=self.session, t_s=1, energy_wh=.03, threshold_wh=.02)

    def test_json_shapes_and_series_limits(self):
        for slug, example in [('cuenca-banco', 'state.example.json'), ('cuenca-sede', 'state.venue.example.json')]:
            actual = self.state(slug)
            expected = json.loads((settings.BASE_DIR.parent / 'contracts' / example).read_text())
            self.assertEqual(actual.keys(), expected.keys())
            self.assertEqual(actual['session'].keys(), expected['session'].keys())
            self.assertEqual(actual['zones'][0].keys(), expected['zones'][0].keys() | {'setpoint_current_a'})
        self.post('advance', {'seconds': 610})
        state = self.state()
        self.assertEqual(len(state['series']['carga-5v']), 600)
        self.assertEqual(len(state['series']['total']), 600)
        report = self.client.get(self.base + '/report').json()
        fixture = json.loads((settings.BASE_DIR.parent / 'contracts/report.example.json').read_text())
        self.assertEqual(report.keys(), fixture.keys())
        self.assertEqual(report['values'].keys(), fixture['values'].keys())

    def test_backup_idempotent_closed_and_preserves_active(self):
        active = list(Session.objects.filter(status='running').values_list('id', flat=True))
        call_command('load_backup_demo', verbosity=0)
        call_command('load_backup_demo', verbosity=0)
        self.assertEqual(Session.objects.filter(backup_key__isnull=False).count(), 2)
        self.assertEqual(set(active), set(Session.objects.filter(status='running').values_list('id', flat=True)))
        backup = Session.objects.get(backup_key='cuenca-banco')
        self.assertEqual(backup.status, 'closed')
        self.assertEqual(backup.elapsed_s, 46)
        self.assertAlmostEqual(backup.energy_wh, .02, places=9)
        self.assertEqual(backup.alerts.count(), 1)
        self.assertEqual(backup.zone_states.get().on_seconds, 36)

    def test_seed_demo_reports_actual_user_count(self):
        out = io.StringIO()
        with patch.dict(os.environ, {'DEMO_OPERATOR_PASSWORD': 'Demo-2026'}):
            call_command('seed_demo', stdout=out)
        self.assertIn('Demo ready: 2 localities, 4 sites, 4 users.', out.getvalue())
        out_three = io.StringIO()
        with patch.dict(os.environ, {'DEMO_OPERATOR_PASSWORD': ''}):
            call_command('seed_demo', stdout=out_three)
        self.assertIn('Demo ready: 2 localities, 4 sites, 3 users.', out_three.getvalue())

    def test_setpoint_current_a_preserved_when_off(self):
        initial = self.state('cuenca-banco')['zones'][0]
        self.assertFalse(initial['on'])
        self.assertEqual(initial['current_a'], 0.0)
        self.assertEqual(initial['power_w'], 0.0)
        self.assertAlmostEqual(initial['setpoint_current_a'], 0.4)

        adjusted = self.post('zones/carga-5v', {'current_a': 0.65})['zones'][0]
        self.assertFalse(adjusted['on'])
        self.assertEqual(adjusted['current_a'], 0.0)
        self.assertEqual(adjusted['power_w'], 0.0)
        self.assertAlmostEqual(adjusted['setpoint_current_a'], 0.65)

        enabled = self.post('zones/carga-5v', {'on': True})['zones'][0]
        self.assertTrue(enabled['on'])
        self.assertAlmostEqual(enabled['current_a'], 0.65)
        self.assertAlmostEqual(enabled['setpoint_current_a'], 0.65)
        self.assertAlmostEqual(enabled['power_w'], 3.25)

        disabled = self.post('zones/carga-5v', {'on': False})['zones'][0]
        self.assertFalse(disabled['on'])
        self.assertEqual(disabled['current_a'], 0.0)
        self.assertAlmostEqual(disabled['setpoint_current_a'], 0.65)

        for zone in self.state('cuenca-sede')['zones']:
            self.assertIsNone(zone['setpoint_current_a'])

    def test_login_rate_limiting(self):
        cache.clear()
        self.addCleanup(cache.clear)
        anon = Client()
        bad = json.dumps({'username': 'operador_cuenca', 'password': 'wrong-password'})
        good = json.dumps({'username': 'operador_cuenca', 'password': os.environ['DEMO_CUENCA_PASSWORD']})
        limit = settings.LOGIN_RATE_LIMIT
        window = settings.LOGIN_RATE_WINDOW_S

        with patch('energy.views.time.time', return_value=1000.0):
            for _ in range(limit):
                r = anon.post('/api/auth/login', bad, content_type='application/json', REMOTE_ADDR='10.0.0.1')
                self.assertEqual(r.status_code, 403)
            blocked = anon.post('/api/auth/login', good, content_type='application/json', REMOTE_ADDR='10.0.0.1')
            self.assertEqual(blocked.status_code, 429)
            self.assertEqual(blocked.json(), {'error': 'rate_limited'})
            self.assertGreaterEqual(int(blocked['Retry-After']), 1)

            # Another client IP is unaffected and multiple valid logins do not trip the limiter.
            for _ in range(limit + 2):
                ok = anon.post('/api/auth/login', good, content_type='application/json', REMOTE_ADDR='10.0.0.2')
                self.assertEqual(ok.status_code, 200)

        # After the window expires, the original IP can log in again and its failure counter resets.
        with patch('energy.views.time.time', return_value=1000.0 + window + 1):
            recovered = anon.post('/api/auth/login', good, content_type='application/json', REMOTE_ADDR='10.0.0.1')
            self.assertEqual(recovered.status_code, 200)
            after_reset = anon.post('/api/auth/login', bad, content_type='application/json', REMOTE_ADDR='10.0.0.1')
            self.assertEqual(after_reset.status_code, 403)


FAKE_WEBHOOK = 'https://discord.invalid/api/webhooks/000/fake-token-for-tests'


class FakeResponse:
    status = 204

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@patch.dict(os.environ, {'DISCORD_WEBHOOK_URL_TEST': FAKE_WEBHOOK})
class DiscordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)

    def setUp(self):
        cache.clear()
        self.client.force_login(get_user_model().objects.get(username='operador_cuenca'))
        self.site = Site.objects.get(slug='cuenca-banco')
        self.session = Session.objects.get(site=self.site, status='running')
        self.base = f'/api/sessions/{self.session.id}'

    def post(self, action, body=None, expected=200):
        response = self.client.post(f'{self.base}/{action}', json.dumps(body or {}), content_type='application/json')
        self.assertEqual(response.status_code, expected, response.content[:500])
        self.assertNotIn('discord.invalid', response.content.decode())
        return response.json()

    def reach_threshold(self):
        self.post('zones/carga-5v', {'on': True, 'current_a': .4})
        with self.captureOnCommitCallbacks(execute=True):
            return self.post('advance', {'seconds': 40})

    def payload_of(self, mocked, call=0):
        request = mocked.call_args_list[call].args[0]
        self.assertEqual(mocked.call_args_list[call].kwargs['timeout'], 5)
        return json.loads(request.data)

    @patch('energy.discord.urllib.request.urlopen', return_value=FakeResponse())
    def test_alert_sent_once_with_units(self, urlopen):
        self.reach_threshold()
        self.assertEqual(urlopen.call_count, 1)
        body = self.payload_of(urlopen)
        self.assertEqual(body['username'], 'Pulso Energético')
        embed = body['embeds'][0]
        values = {f['name']: f['value'] for f in embed['fields']}
        self.assertTrue(values['Energía acumulada'].endswith(' Wh'))
        self.assertEqual(values['Umbral'], '0,0200 Wh')
        self.assertEqual(values['Hora del escenario'], '08:00:36')
        self.assertEqual(embed['footer']['text'], 'Datos simulados · Prototipo hackatón Ecuador × Chile')
        self.assertIsNotNone(Alert.objects.get(session=self.session).discord_sent_at)
        self.assertEqual(AuditEvent.objects.get(session=self.session, action='discord.alert').payload,
                         {'ok': True, 'http_status': 204})
        with self.captureOnCommitCallbacks(execute=True):
            self.post('zones/carga-5v', {'on': False})
            self.post('zones/carga-5v', {'on': True})
            self.post('advance', {'seconds': 30})
        self.assertEqual(urlopen.call_count, 1)
        from .services import send_alert
        self.assertFalse(send_alert(Alert.objects.get(session=self.session).id, '08:00:00'))
        self.assertEqual(urlopen.call_count, 1)
        state = self.client.get('/api/sites/cuenca-banco/state').json()
        self.assertEqual(state['discord']['label'], 'Enviado a Discord')
        self.assertTrue(state['discord']['configured'])
        self.assertIsNotNone(state['discord']['last_sent_at'])
        report = self.client.get(f'{self.base}/report').json()
        self.assertEqual(report['discord_preview'], {**report['discord_preview'], 'label': 'Enviado a Discord', 'sent': True})

    @patch('energy.discord.urllib.request.urlopen', return_value=FakeResponse())
    def test_venue_alert_uses_kwh(self, urlopen):
        site = Site.objects.get(slug='cuenca-sede')
        session = Session.objects.get(site=site, status='running')
        session.threshold_wh = 1
        session.save()
        self.client.post(f'/api/sessions/{session.id}/zones/salon-principal', json.dumps({'on': True}),
                         content_type='application/json')
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(f'/api/sessions/{session.id}/advance', json.dumps({'seconds': 600}),
                                        content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content[:300])
        values = {f['name']: f['value'] for f in self.payload_of(urlopen)['embeds'][0]['fields']}
        self.assertTrue(values['Umbral'].endswith(' kWh'))

    @patch('energy.discord.urllib.request.urlopen')
    def test_without_webhook_nothing_sent(self, urlopen):
        with patch.dict(os.environ, {'DISCORD_WEBHOOK_URL_TEST': ''}):
            self.reach_threshold()
            urlopen.assert_not_called()
            state = self.client.get('/api/sites/cuenca-banco/state').json()
            self.assertEqual(state['discord'], {**state['discord'], 'configured': False, 'last_sent_at': None,
                                                'label': 'Simulación local', 'sent': False})
            report = self.client.get(f'{self.base}/report').json()
            self.assertEqual(report['discord_preview']['label'], 'Simulación local')
            self.post('discord/report', expected=409)
        self.assertIsNone(Alert.objects.get(session=self.session).discord_sent_at)

    def test_configured_label_before_sending(self):
        state = self.client.get('/api/sites/cuenca-banco/state').json()
        self.assertEqual(state['discord']['label'], 'Discord configurado')
        self.assertNotIn('discord.invalid', json.dumps(state))

    @patch('energy.discord.urllib.request.urlopen', side_effect=TimeoutError())
    def test_discord_failure_does_not_break_request(self, urlopen):
        with self.assertLogs('energy.discord', 'WARNING') as logs:
            result = self.reach_threshold()
        self.assertTrue(result['session']['alert_fired'])
        self.assertEqual(urlopen.call_count, 1)
        self.assertNotIn('discord.invalid', '\n'.join(logs.output))
        self.assertIsNone(Alert.objects.get(session=self.session).discord_sent_at)
        self.assertEqual(self.client.get('/api/sites/cuenca-banco/state').json()['discord']['label'],
                         'Discord configurado')

    def test_http_error_logs_only_status(self):
        import urllib.error
        error = urllib.error.HTTPError(FAKE_WEBHOOK, 500, 'boom', {}, None)
        with patch('energy.discord.urllib.request.urlopen', side_effect=error), \
                self.assertLogs('energy.discord', 'WARNING') as logs:
            self.reach_threshold()
        self.assertIn('HTTP 500', '\n'.join(logs.output))
        self.assertNotIn('discord.invalid', '\n'.join(logs.output))

    @patch('energy.discord.urllib.request.urlopen', return_value=FakeResponse())
    def test_report_requires_operator_and_csrf(self, urlopen):
        observer = Client()
        observer.force_login(get_user_model().objects.get(username='observador'))
        self.assertEqual(observer.post(f'{self.base}/discord/report').status_code, 403)
        self.assertEqual(Client().post(f'{self.base}/discord/report').status_code, 403)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(get_user_model().objects.get(username='operador_cuenca'))
        self.assertEqual(strict.post(f'{self.base}/discord/report').status_code, 403)
        urlopen.assert_not_called()
        strict.get('/api/auth/csrf')
        token = strict.cookies['csrftoken'].value
        response = strict.post(f'{self.base}/discord/report', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200, response.content[:300])
        self.assertNotIn('discord.invalid', response.content.decode())
        self.assertEqual(urlopen.call_count, 1)
        embed = self.payload_of(urlopen)['embeds'][0]
        self.assertIn('Resumen del ensayo', embed['description'])
        self.assertTrue(response.json()['discord']['report_sent'])
        self.assertTrue(AuditEvent.objects.filter(session=self.session, action='discord.report').exists())
        self.assertEqual(self.client.get(f'{self.base}/discord/report').status_code, 405)

    @patch('energy.discord.urllib.request.urlopen', return_value=FakeResponse())
    def test_report_rate_limit_30s(self, urlopen):
        self.post('discord/report')
        response = self.client.post(f'{self.base}/discord/report')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {'error': 'rate_limited'})
        self.assertTrue(1 <= int(response['Retry-After']) <= 30)
        self.assertEqual(urlopen.call_count, 1)
        with patch('energy.views.time.time', return_value=__import__('time').time() + 31):
            cache.delete(f'discord_report:{self.session.id}')  # la entrada caduca a los 30 s
            self.post('discord/report')
        self.assertEqual(urlopen.call_count, 2)

    def test_report_discord_429_and_failure(self):
        import urllib.error
        error = urllib.error.HTTPError(FAKE_WEBHOOK, 429, 'slow down', {'Retry-After': '7.2'}, None)
        with patch('energy.discord.urllib.request.urlopen', side_effect=error) as urlopen:
            response = self.client.post(f'{self.base}/discord/report')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response['Retry-After'], '8')
        self.assertEqual(urlopen.call_count, 1)
        cache.clear()
        with patch('energy.discord.urllib.request.urlopen', side_effect=OSError()):
            response = self.client.post(f'{self.base}/discord/report')
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {'error': 'discord_unavailable'})
        self.assertNotIn('discord.invalid', response.content.decode())
