from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from energy.models import Site, Session
from energy.services import new_session, immediate, advance, audit


class Command(BaseCommand):
    help = 'Load two closed rehearsals, locally and idempotently; keep active sessions intact.'

    @transaction.atomic
    def handle(self, *args, **options):
        call_command('seed_demo')
        for slug in ['cuenca-banco', 'cuenca-sede']:
            site = Site.objects.select_for_update().get(slug=slug)
            if Session.objects.filter(backup_key=slug).exists():
                continue
            # Build the backup without closing the user's current active rehearsal.
            session = Session.objects.create(site=site, status='closed', backup_key=slug,
                threshold_wh=.02 if site.kind == 'bench' else 600, speed=site.default_speed)
            from energy.models import ZoneState
            for zone in site.zones.all():
                ZoneState.objects.create(session=session, zone=zone, on=True)
            immediate(session)
            if site.kind == 'bench':
                advance(session, 18)
                session.zone_states.update(on=False)
                immediate(session)
                advance(session, 10)
                session.zone_states.update(on=True)
                immediate(session)
                advance(session, 18)
                session.zone_states.update(on=False)
                immediate(session)
            else:
                for _ in range(3):
                    advance(session, 3600)
                session.zone_states.filter(zone__slug='sala-reuniones').update(on=False)
                immediate(session)
                for _ in range(3):
                    advance(session, 3600)
                session.zone_states.update(on=False)
                immediate(session)
            session.closed_at = timezone.now()
            session.save()
            audit(None, session, 'load_backup_demo')
            self.stdout.write(f'{slug}: /api/sessions/{session.id}/report')
