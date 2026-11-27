import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from energy.models import Locality, Site, Zone, Session
from energy.services import new_session, audit


class Command(BaseCommand):
    help = 'Create the demo without replacing existing sessions, controls or passwords.'

    @transaction.atomic
    def handle(self, *args, **options):
        users = {}
        for username, variable in [('operador_cuenca', 'DEMO_CUENCA_PASSWORD'),
                                   ('operador_puente', 'DEMO_PUENTE_PASSWORD'),
                                   ('observador', 'DEMO_OBSERVER_PASSWORD')]:
            password = os.getenv(variable)
            if not password:
                raise CommandError(f'{variable} is required')
            user, created = get_user_model().objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.save()
            users[username] = user
        # Operador de presentación: opera las dos localidades (opcional; se omite si no hay contraseña).
        demo_password = os.getenv('DEMO_OPERATOR_PASSWORD')
        if demo_password:
            demo_user, created = get_user_model().objects.get_or_create(username='operador_demo')
            if created:
                demo_user.set_password(demo_password)
                demo_user.save()
            users['operador_demo'] = demo_user
        for slug, name, country, tz, voltage, venue, operator in [
            ('cuenca', 'Cuenca', 'Ecuador', 'America/Guayaquil', 120,
             'Centro Comunitario Río Tomebamba (ficticio)', 'operador_cuenca'),
            ('puente-alto', 'Puente Alto', 'Chile', 'America/Santiago', 220,
             'Sede Vecinal Los Andes (ficticia)', 'operador_puente')]:
            loc, _ = Locality.objects.get_or_create(slug=slug, defaults=dict(name=name, country=country, timezone=tz))
            for kind, suffix in [('bench', 'banco'), ('venue', 'sede')]:
                bench = kind == 'bench'
                site, created = Site.objects.get_or_create(slug=f'{slug}-{suffix}', defaults={
                    'locality': loc, 'name': 'Banco de pruebas 5 V' if bench else venue, 'kind': kind,
                    'fictitious': not bench, 'budget_kwh_day': None if bench else .6,
                    'sample_interval_s': 1 if bench else 60, 'default_speed': 1 if bench else 60})
                site.operators.add(users[operator])
                if 'operador_demo' in users:
                    site.operators.add(users['operador_demo'])
                zones = [('carga-5v', 'Carga simulada 5 V', 'dc_load', False, 5, 4, .8)] if bench else [
                    ('salon-principal', 'Salón principal', 'light', False, voltage, 160, None),
                    ('sala-reuniones', 'Sala de reuniones', 'light', True, voltage, 80, None)]
                for zslug, zname, zkind, dimmable, volts, watts, maximum in zones:
                    Zone.objects.get_or_create(site=site, slug=zslug, defaults={'name': zname, 'kind': zkind,
                        'dimmable': dimmable, 'nominal_voltage_v': volts, 'nominal_power_w': watts, 'max_current_a': maximum})
                if not Session.objects.filter(site=site, status='running').exists():
                    session = new_session(site)
                    audit(None, session, 'seed_demo')
        self.stdout.write(self.style.SUCCESS(f'Demo ready: 2 localities, 4 sites, {len(users)} users.'))
