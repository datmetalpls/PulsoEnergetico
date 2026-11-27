import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Locality(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    timezone = models.CharField(max_length=100)


class Site(models.Model):
    slug = models.SlugField(unique=True)
    locality = models.ForeignKey(Locality, on_delete=models.CASCADE, related_name='sites')
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=[('bench', 'bench'), ('venue', 'venue')])
    fictitious = models.BooleanField(default=False)
    budget_kwh_day = models.FloatField(null=True)
    sample_interval_s = models.PositiveIntegerField()
    default_speed = models.PositiveIntegerField()
    operators = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='operable_sites')


class Zone(models.Model):
    slug = models.SlugField()
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='zones')
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=10)
    dimmable = models.BooleanField(default=False)
    nominal_voltage_v = models.FloatField()
    nominal_power_w = models.FloatField()
    max_current_a = models.FloatField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['site', 'slug'], name='zone_site_slug')]
        ordering = ['id']


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='sessions')
    status = models.CharField(max_length=10, default='running')
    started_at = models.DateTimeField(default=timezone.now)
    threshold_wh = models.FloatField()
    elapsed_s = models.PositiveIntegerField(default=0)
    scenario_start = models.CharField(max_length=5, default='08:00')
    scenario_offset_s = models.PositiveIntegerField(default=0)
    playing = models.BooleanField(default=False)
    speed = models.PositiveIntegerField(default=1)
    last_tick_wall = models.DateTimeField(default=timezone.now)
    connected = models.BooleanField(default=True)
    energy_wh = models.FloatField(default=0)
    alert_fired = models.BooleanField(default=False)
    active_source = models.CharField(max_length=20, default='simulator')
    telemetry_origin = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    backup_key = models.CharField(max_length=50, unique=True, null=True)
    discord_report_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['site'], condition=Q(status='running'), name='one_running_session')]


class ZoneState(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='zone_states')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)
    on = models.BooleanField(default=False)
    current_a = models.FloatField(default=0.4)
    intensity_pct = models.FloatField(default=100)
    power_w = models.FloatField(default=0)
    energy_wh = models.FloatField(default=0)
    on_seconds = models.FloatField(default=0)
    last_t_s = models.FloatField(null=True)
    gap_pending = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['session', 'zone'], name='one_zone_state')]


class Reading(models.Model):
    reading_id = models.CharField(max_length=200, unique=True)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='readings')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)
    t_s = models.FloatField()
    instant = models.DateTimeField()
    voltage_v = models.FloatField()
    current_a = models.FloatField()
    power_w = models.FloatField()
    interval_wh = models.FloatField(default=0)
    energy_wh = models.FloatField(default=0)
    flag = models.CharField(max_length=20, default='ok')
    source = models.CharField(max_length=20)


class Gap(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='gaps')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)
    from_t_s = models.FloatField()
    to_t_s = models.FloatField()
    reason = models.CharField(max_length=100, default='Conexión interrumpida')


class Alert(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='alerts')
    kind = models.CharField(max_length=20, default='threshold')
    t_s = models.FloatField()
    energy_wh = models.FloatField()
    threshold_wh = models.FloatField()
    acknowledged_at = models.DateTimeField(null=True)
    channel = models.CharField(max_length=20, default='browser')
    discord_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['session', 'kind'], name='one_threshold_alert')]


class AuditEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    session = models.ForeignKey(Session, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    at = models.DateTimeField(default=timezone.now)
