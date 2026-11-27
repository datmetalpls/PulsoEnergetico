import { Injectable, computed, effect, inject, signal } from '@angular/core';
import { catchError, of } from 'rxjs';
import {
  AuthMeResponse,
  BandKey,
  ComparisonResponse,
  LocalityWithSites,
  MockStateKey,
  ReportResponse,
  StateResponse,
} from '../models/pulso.models';
import { AudioAlertService } from './audio-alert.service';
import { MockDataService } from './mock-data.service';
import { PulsoApiService } from './pulso-api.service';

@Injectable({ providedIn: 'root' })
export class PulsoStoreService {
  private readonly api = inject(PulsoApiService);
  private readonly mock = inject(MockDataService);
  private readonly audio = inject(AudioAlertService);

  readonly isMockMode = signal(
    typeof window !== 'undefined' &&
      new URLSearchParams(window.location.search).get('mock') === '1'
  );

  readonly localities = signal<LocalityWithSites[]>([]);
  readonly selectedLocalitySlug = signal<string>('cuenca');
  readonly selectedSiteSlug = signal<string>('cuenca-banco');

  readonly state = signal<StateResponse | null>(null);
  readonly report = signal<ReportResponse | null>(null);
  readonly comparison = signal<ComparisonResponse | null>(null);

  readonly auth = signal<AuthMeResponse>({
    authenticated: false,
    username: 'observador',
    role: 'observer',
    operable_sites: [],
  });

  readonly mockState = signal<MockStateKey>('encendida');
  readonly mockBand = signal<BandKey>('day');
  readonly mockRole = signal<'operator' | 'observer'>('operator');

  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);

  private pollTimer: ReturnType<typeof setInterval> | null = null;

  readonly currentBand = computed<BandKey>(() => {
    return this.state()?.session.band ?? this.mockBand();
  });

  readonly activeAlerts = computed(() => {
    return this.state()?.alerts ?? [];
  });

  readonly hasUnacknowledgedAlert = computed(() => {
    const s = this.state();
    if (!s) return false;
    return s.session.alert_fired || s.alerts.length > 0;
  });

  readonly totalGapSeconds = computed(() => {
    const gaps = this.state()?.gaps ?? [];
    return gaps.reduce((sum, g) => sum + g.duration_s, 0);
  });

  readonly canOperate = computed(() => {
    return this.state()?.permissions.can_operate ?? false;
  });

  readonly availableSitesForLocality = computed(() => {
    const loc = this.localities().find(
      (l) => l.slug === this.selectedLocalitySlug()
    );
    return loc?.sites ?? [];
  });

  constructor() {
    effect(() => {
      const s = this.state();
      if (typeof document !== 'undefined') {
        const hasAlert = s ? s.session.alert_fired || s.alerts.length > 0 : false;
        document.title = hasAlert ? '⚠ Pulso Energético' : 'Pulso Energético';
      }
      if (s && s.alerts.length > 0) {
        for (const alert of s.alerts) {
          if (!alert.acknowledged) {
            this.audio.triggerAlertBeepIfNew(alert.id);
          }
        }
      }
    });
  }

  init(): void {
    if (this.isMockMode()) {
      this.loading.set(true);
      this.mock.loadFixtures().subscribe({
        next: () => {
          this.localities.set(this.mock.getLocalities());
          this.auth.set({
            authenticated: true,
            username: 'operador_cuenca',
            role: 'operator',
            operable_sites: [
              'cuenca-banco',
              'cuenca-sede',
              'puente-alto-banco',
              'puente-alto-sede',
            ],
          });
          this.applyMockView();
          this.loading.set(false);
        },
        error: () => {
          this.errorMessage.set('No se pudieron cargar los fixtures locales.');
          this.loading.set(false);
        },
      });
      return;
    }

    this.loading.set(true);
    this.api.getCsrf().pipe(catchError(() => of(null))).subscribe(() => {
      this.refreshAuthAndLocalities();
    });

    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', this.onVisibilityChange);
    }
    this.startPolling();
  }

  destroy(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    if (typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', this.onVisibilityChange);
    }
  }

  private readonly onVisibilityChange = (): void => {
    if (!this.isMockMode() && document.visibilityState === 'visible') {
      this.fetchCurrentState();
    }
  };

  private startPolling(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
    }
    this.pollTimer = setInterval(() => {
      if (
        !this.isMockMode() &&
        typeof document !== 'undefined' &&
        document.visibilityState === 'visible'
      ) {
        this.fetchCurrentState();
      }
    }, 1000);
  }

  private refreshAuthAndLocalities(): void {
    this.api
      .getMe()
      .pipe(catchError(() => of(this.auth())))
      .subscribe((me) => this.auth.set(me));

    this.api
      .getLocalities()
      .pipe(
        catchError(() => {
          this.errorMessage.set(
            'Backend no disponible en /api. Usa ?mock=1 para el prototipo navegable.'
          );
          this.loading.set(false);
          return of([]);
        })
      )
      .subscribe((locs) => {
        if (locs.length > 0) {
          this.localities.set(locs);
          this.selectedLocalitySlug.set(locs[0].slug);
          if (locs[0].sites.length > 0) {
            this.selectedSiteSlug.set(locs[0].sites[0].slug);
            this.fetchCurrentState();
          }
        }
        this.loading.set(false);
      });
  }

  fetchCurrentState(): void {
    const slug = this.selectedSiteSlug();
    if (!slug || this.isMockMode()) return;

    this.api
      .getState(slug)
      .pipe(
        catchError((err) => {
          this.errorMessage.set(
            err?.error?.error || 'Error al consultar el estado del backend.'
          );
          return of(null);
        })
      )
      .subscribe((s) => {
        if (s) {
          this.errorMessage.set(null);
          this.state.set(s);
          if (s.site.kind === 'venue' && !this.comparison()) {
            this.loadComparison();
          }
        }
      });
  }

  selectLocality(localitySlug: string): void {
    this.selectedLocalitySlug.set(localitySlug);
    const loc = this.localities().find((l) => l.slug === localitySlug);
    if (loc && loc.sites.length > 0) {
      this.selectSite(loc.sites[0].slug);
    }
  }

  selectSite(siteSlug: string): void {
    this.selectedSiteSlug.set(siteSlug);
    this.report.set(null);
    this.comparison.set(null);
    if (this.isMockMode()) {
      this.applyMockView();
    } else {
      this.fetchCurrentState();
    }
  }

  setMockState(key: MockStateKey): void {
    this.mockState.set(key);
    this.applyMockView();
  }

  setMockBand(band: BandKey): void {
    this.mockBand.set(band);
    this.applyMockView();
  }

  private applyMockView(): void {
    const built = this.mock.buildState(
      this.selectedSiteSlug(),
      this.mockState(),
      this.mockBand(),
      this.mockRole()
    );
    this.state.set(built);
    if (this.mockState() === 'reporte') {
      this.report.set(this.mock.buildReport(built));
    } else {
      this.report.set(null);
    }
    if (built.site.kind === 'venue') {
      this.comparison.set(this.mock.buildComparison(built.site.slug));
    } else {
      this.comparison.set(null);
    }
  }

  login(username: string, password: string): void {
    if (this.isMockMode()) {
      const role: 'operator' | 'observer' = username.includes('observ')
        ? 'observer'
        : 'operator';
      this.mockRole.set(role);
      this.auth.set({
        authenticated: true,
        username: username || (role === 'operator' ? 'operador_cuenca' : 'observador'),
        role,
        operable_sites:
          role === 'operator'
            ? ['cuenca-banco', 'cuenca-sede', 'puente-alto-banco', 'puente-alto-sede']
            : [],
      });
      this.applyMockView();
      return;
    }

    this.api
      .login(username, password)
      .pipe(
        catchError(() => {
          this.errorMessage.set('Credenciales inválidas o error de sesión.');
          return of(null);
        })
      )
      .subscribe((me) => {
        if (me) {
          this.errorMessage.set(null);
          this.auth.set(me);
          this.fetchCurrentState();
        }
      });
  }

  logout(): void {
    if (this.isMockMode()) {
      this.mockRole.set('observer');
      this.auth.set({
        authenticated: false,
        username: 'observador',
        role: 'observer',
        operable_sites: [],
      });
      this.applyMockView();
      return;
    }

    this.api.logout().subscribe(() => {
      this.auth.set({
        authenticated: false,
        username: 'observador',
        role: 'observer',
        operable_sites: [],
      });
      this.fetchCurrentState();
    });
  }

  startSession(): void {
    const s = this.state();
    if (!s) return;
    if (this.isMockMode()) {
      this.setMockState('encendida');
      return;
    }
    this.api.startSession(s.site.slug).subscribe((next) => this.state.set(next));
  }

  play(): void {
    const s = this.state();
    if (!s) return;
    if (this.isMockMode()) {
      this.state.set({ ...s, session: { ...s.session, playing: true } });
      return;
    }
    this.api.play(s.session.id).subscribe((next) => this.state.set(next));
  }

  pause(): void {
    const s = this.state();
    if (!s) return;
    if (this.isMockMode()) {
      this.state.set({ ...s, session: { ...s.session, playing: false } });
      return;
    }
    this.api.pause(s.session.id).subscribe((next) => this.state.set(next));
  }

  nextBand(): void {
    const s = this.state();
    if (!s) return;
    if (this.isMockMode()) {
      const order: BandKey[] = ['day', 'afternoon', 'night'];
      const nextIdx = (order.indexOf(this.mockBand()) + 1) % order.length;
      this.setMockBand(order[nextIdx]);
      return;
    }
    this.api.nextBand(s.session.id).subscribe((next) => this.state.set(next));
  }

  setSpeed(speed: number): void {
    const s = this.state();
    if (!s) return;
    if (this.isMockMode()) {
      this.state.set({ ...s, session: { ...s.session, speed } });
      return;
    }
    this.api.setSpeed(s.session.id, speed).subscribe((next) => this.state.set(next));
  }

  toggleZone(zoneSlug: string): void {
    const s = this.state();
    if (!s) return;
    const zone = s.zones.find((z) => z.slug === zoneSlug);
    if (!zone) return;
    const nextOn = !zone.on;

    if (this.isMockMode()) {
      const nextZones = s.zones.map((z) => {
        if (z.slug !== zoneSlug) return z;
        const currentA = nextOn ? (z.current_a > 0 ? z.current_a : 0.4) : 0;
        const powerW = nextOn
          ? z.dimmable
            ? Number(((80 * (z.intensity_pct ?? 75)) / 100).toFixed(2))
            : z.kind === 'dc_load'
              ? Number((z.voltage_v * currentA).toFixed(2))
              : 160
          : 0;
        return {
          ...z,
          on: nextOn,
          current_a: currentA,
          power_w: powerW,
          indicator: {
            led: (nextOn ? 'green' : 'off') as 'green' | 'off',
            label: nextOn
              ? z.kind === 'dc_load'
                ? 'Carga habilitada'
                : 'Encendida'
              : z.kind === 'dc_load'
                ? 'Carga deshabilitada'
                : 'Apagada',
          },
        };
      });
      const totalPower = nextZones.reduce((sum, z) => sum + z.power_w, 0);
      this.state.set({
        ...s,
        zones: nextZones,
        session: {
          ...s.session,
          total_power_w: totalPower,
          time_to_threshold_s:
            totalPower > 0 ? Math.round((s.session.remaining_wh * 3600) / totalPower) : null,
          status_label: totalPower > 0 ? 'Consumiendo' : 'Consumo detenido',
        },
      });
      return;
    }

    this.api
      .updateZone(s.session.id, zoneSlug, { on: nextOn })
      .subscribe((next) => this.state.set(next));
  }

  setBenchCurrent(zoneSlug: string, currentA: number): void {
    const s = this.state();
    if (!s) return;
    if (this.isMockMode()) {
      const nextZones = s.zones.map((z) => {
        if (z.slug !== zoneSlug) return z;
        const powerW = z.on ? Number((z.voltage_v * currentA).toFixed(2)) : 0;
        return { ...z, current_a: currentA, power_w: powerW };
      });
      const totalPower = nextZones.reduce((sum, z) => sum + z.power_w, 0);
      this.state.set({
        ...s,
        zones: nextZones,
        session: {
          ...s.session,
          total_power_w: totalPower,
          time_to_threshold_s:
            totalPower > 0 ? Math.round((s.session.remaining_wh * 3600) / totalPower) : null,
        },
      });
      return;
    }
    this.api
      .updateZone(s.session.id, zoneSlug, { current_a: currentA })
      .subscribe((next) => this.state.set(next));
  }

  setZoneIntensity(zoneSlug: string, intensityPct: number): void {
    const s = this.state();
    if (!s) return;
    if (this.isMockMode()) {
      const nextZones = s.zones.map((z) => {
        if (z.slug !== zoneSlug) return z;
        const powerW = z.on ? Number(((80 * intensityPct) / 100).toFixed(2)) : 0;
        return { ...z, intensity_pct: intensityPct, power_w: powerW };
      });
      const totalPower = nextZones.reduce((sum, z) => sum + z.power_w, 0);
      this.state.set({
        ...s,
        zones: nextZones,
        session: {
          ...s.session,
          total_power_w: totalPower,
          time_to_threshold_s:
            totalPower > 0 ? Math.round((s.session.remaining_wh * 3600) / totalPower) : null,
        },
      });
      return;
    }
    this.api
      .updateZone(s.session.id, zoneSlug, { intensity_pct: intensityPct })
      .subscribe((next) => this.state.set(next));
  }

  toggleConnection(): void {
    const s = this.state();
    if (!s) return;
    const nextConn = !s.session.connected;
    if (this.isMockMode()) {
      this.setMockState(nextConn ? 'encendida' : 'sin_conexion');
      return;
    }
    this.api
      .setConnection(s.session.id, nextConn)
      .subscribe((next) => this.state.set(next));
  }

  ackAlert(alertId: string): void {
    const s = this.state();
    if (!s) return;
    if (this.isMockMode()) {
      this.state.set({
        ...s,
        alerts: s.alerts.map((a) =>
          a.id === alertId ? { ...a, acknowledged: true } : a
        ),
      });
      return;
    }
    this.api.ackAlert(s.session.id, alertId).subscribe((next) => this.state.set(next));
  }

  loadReport(): void {
    const s = this.state();
    if (!s) return;
    if (this.isMockMode()) {
      this.report.set(this.mock.buildReport(s));
      return;
    }
    this.api.getReport(s.session.id).subscribe((rep) => this.report.set(rep));
  }

  loadComparison(): void {
    const s = this.state();
    if (!s || s.site.kind !== 'venue') return;
    if (this.isMockMode()) {
      this.comparison.set(this.mock.buildComparison(s.site.slug));
      return;
    }
    this.api.getComparison(s.site.slug).subscribe((cmp) => this.comparison.set(cmp));
  }
}
