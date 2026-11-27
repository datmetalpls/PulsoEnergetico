import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import get_user_model
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

    def test_catch_up_lock_idempotency_and_cap(self):
        self.post('zones/carga-5v', {'on': True})
        self.session.refresh_from_db()
        now = timezone.now()
        self.session.playing, self.session.last_tick_wall = True, now - timedelta(seconds=130)
        self.session.save()
        with patch('energy.services.timezone.now', return_value=now):
            with transaction.atomic():
                session = Session.objects.select_for_update().get(id=self.session.id)
                catch_up(session)
            with transaction.atomic():
                again = Session.objects.select_for_update().get(id=self.session.id)
                catch_up(again)
        self.assertEqual(again.elapsed_s, 130)
        self.assertAlmostEqual(again.energy_wh, 2 * 120 / 3600)
        self.assertEqual(again.gaps.get().to_t_s - again.gaps.get().from_t_s, 10)
        self.assertEqual(again.readings.count(), session.readings.count())

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
            self.assertEqual(actual['zones'][0].keys(), expected['zones'][0].keys())
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
