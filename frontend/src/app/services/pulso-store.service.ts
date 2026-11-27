import { HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, effect, inject, signal } from '@angular/core';
import { Observable, catchError, of } from 'rxjs';
import {
  AuthMeResponse,
  BandKey,
  LocalityWithSites,
  MockStateKey,
  StateResponse,
  ZoneState,
} from '../models/pulso.models';
import { AudioAlertService } from './audio-alert.service';
import { MockDataService } from './mock-data.service';
import { PulsoApiService } from './pulso-api.service';

const DEFAULT_BENCH_CURRENT_A = 0.4;
const SLIDER_DEBOUNCE_MS = 250;
const ACTION_FEEDBACK_MS = 6000;

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

  /**
   * Presentation-only memory of the bench knob setpoint (A) per site+zone.
   * Fallback when backend does not provide `setpoint_current_a`.
   */
  readonly benchCurrentRemembered = signal<Record<string, number>>({});

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
  readonly actionFeedback = signal<string | null>(null);

  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private feedbackTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly sliderTimers = new Map<string, ReturnType<typeof setTimeout>>();
  private readonly lastSentSliderValue = new Map<string, number>();

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
    if (this.feedbackTimer) {
      clearTimeout(this.feedbackTimer);
      this.feedbackTimer = null;
    }
    for (const timer of this.sliderTimers.values()) {
      clearTimeout(timer);
    }
    this.sliderTimers.clear();
    if (typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', this.onVisibilityChange);
    }
  }

  dismissActionFeedback(): void {
    if (this.feedbackTimer) {
      clearTimeout(this.feedbackTimer);
      this.feedbackTimer = null;
    }
    this.actionFeedback.set(null);
  }

  private showActionFeedback(message: string): void {
    this.actionFeedback.set(message);
    if (this.feedbackTimer) {
      clearTimeout(this.feedbackTimer);
    }
    this.feedbackTimer = setTimeout(() => {
      this.actionFeedback.set(null);
      this.feedbackTimer = null;
    }, ACTION_FEEDBACK_MS);
  }

  private formatActionError(err: HttpErrorResponse): string {
    if (err?.status === 403) {
      return 'Solo lectura: tu usuario no tiene permiso para operar este recinto.';
    }
    if (err?.status === 409 || err?.error?.error === 'session_closed') {
      return 'El ensayo terminó; inicia uno nuevo.';
    }
    if (err?.status === 429 || err?.error?.error === 'rate_limited') {
      const retryHeader = err.headers?.get('Retry-After');
      const seconds = retryHeader ? Math.max(1, Number.parseInt(retryHeader, 10) || 60) : 60;
      return `Demasiados intentos, espera ${seconds} s`;
    }
    return err?.error?.error || 'No se pudo completar la acción en el servidor.';
  }

  private runAction(obs$: Observable<StateResponse>): void {
    obs$
      .pipe(
        catchError((err: HttpErrorResponse) => {
          this.showActionFeedback(this.formatActionError(err));
          if (err?.status === 409 || err?.status === 403) {
            this.fetchCurrentState();
          }
          return of(null);
        })
      )
      .subscribe((next) => {
        if (next) {
          this.errorMessage.set(null);
          this.dismissActionFeedback();
          this.applyState(next);
        }
      });
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
        this.auth().authenticated &&
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
      .subscribe((me) => {
        this.auth.set(me);
        if (!me.authenticated) {
          this.loading.set(false);
          this.errorMessage.set('Inicia sesión para consultar el recinto o banco de pruebas.');
          return;
        }
        this.loadLocalitiesAndState();
      });
  }

  private loadLocalitiesAndState(): void {
    this.api
      .getLocalities()
      .pipe(
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            err?.status === 403
              ? 'Inicia sesión para acceder a las localidades.'
              : 'Backend no disponible en /api. Usa ?mock=1 para el prototipo navegable.'
          );
          this.loading.set(false);
          return of([]);
        })
      )
      .subscribe((locs) => {
        if (locs.length > 0) {
          this.localities.set(locs);
          const currentLoc = locs.find((l) => l.slug === this.selectedLocalitySlug()) ?? locs[0];
          this.selectedLocalitySlug.set(currentLoc.slug);
          if (currentLoc.sites.length > 0) {
            const currentSite =
              currentLoc.sites.find((s) => s.slug === this.selectedSiteSlug()) ??
              currentLoc.sites[0];
            this.selectedSiteSlug.set(currentSite.slug);
            this.fetchCurrentState();
          }
        }
        this.loading.set(false);
      });
  }

  private knobKey(siteSlug: string, zoneSlug: string): string {
    return `${siteSlug}:${zoneSlug}`;
  }

  private applyState(next: StateResponse): void {
    const remembered = this.benchCurrentRemembered();
    let updated: Record<string, number> | null = null;

    // Preserve active optimistic slider values while a debounced write is pending
    const preservedZones = next.zones.map((z) => {
      const hasPendingBench = this.sliderTimers.has(`bench:${z.slug}`);
      const hasPendingDim = this.sliderTimers.has(`dim:${z.slug}`);
      if (z.kind === 'dc_load' && !hasPendingBench) {
        const val = z.setpoint_current_a ?? (z.on && z.current_a > 0 ? z.current_a : null);
        if (val !== null) {
          const key = this.knobKey(next.site.slug, z.slug);
          if (remembered[key] !== val) {
            updated ??= { ...remembered };
            updated[key] = val;
          }
        }
      }
      if (hasPendingBench) {
        const key = this.knobKey(next.site.slug, z.slug);
        const pendingCurrent = remembered[key];
        if (pendingCurrent !== undefined) {
          return { ...z, setpoint_current_a: pendingCurrent };
        }
      }
      if (hasPendingDim) {
        const currentZone = this.state()?.zones.find((cur) => cur.slug === z.slug);
        if (currentZone && currentZone.intensity_pct !== null) {
          return { ...z, intensity_pct: currentZone.intensity_pct };
        }
      }
      return z;
    });

    if (updated) {
      this.benchCurrentRemembered.set(updated);
    }
    this.state.set({ ...next, zones: preservedZones });
  }

  getBenchKnobCurrent(zone: ZoneState): number {
    if (zone.setpoint_current_a !== undefined && zone.setpoint_current_a !== null) {
      return zone.setpoint_current_a;
    }
    if (zone.on && zone.current_a > 0) {
      return zone.current_a;
    }
    const siteSlug = this.state()?.site.slug ?? this.selectedSiteSlug();
    const remembered = this.benchCurrentRemembered()[this.knobKey(siteSlug, zone.slug)];
    if (remembered !== undefined) {
      return remembered;
    }
    if (zone.current_a > 0) {
      return zone.current_a;
    }
    const maxA = zone.max_current_a ?? DEFAULT_BENCH_CURRENT_A;
    return Number(Math.min(DEFAULT_BENCH_CURRENT_A, maxA).toFixed(2));
  }

  private computeMockStatusLabel(s: StateResponse, totalPower: number): string {
    if (s.session.alert_fired) return 'Presupuesto alcanzado';
    if (!s.session.connected) return 'Conexión interrumpida';
    if (s.session.status === 'idle') return 'Ensayo sin iniciar';
    return totalPower > 0 ? 'Consumiendo' : 'Consumo detenido';
  }

  fetchCurrentState(): void {
    const slug = this.selectedSiteSlug();
    if (!slug || this.isMockMode()) return;

    this.api
      .getState(slug)
      .pipe(
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(this.formatActionError(err));
          return of(null);
        })
      )
      .subscribe((s) => {
        if (s) {
          this.errorMessage.set(null);
          this.applyState(s);
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
    this.dismissActionFeedback();
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
    this.applyState(built);
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
        catchError((err: HttpErrorResponse) => {
          if (err?.status === 429 || err?.error?.error === 'rate_limited') {
            const retryHeader = err.headers?.get('Retry-After');
            const seconds = retryHeader ? Math.max(1, Number.parseInt(retryHeader, 10) || 60) : 60;
            this.errorMessage.set(`Demasiados intentos, espera ${seconds} s`);
          } else {
            this.errorMessage.set('Credenciales inválidas o error de sesión.');
          }
          return of(null);
        })
      )
      .subscribe((me) => {
        if (me) {
          this.errorMessage.set(null);
          this.dismissActionFeedback();
          this.auth.set(me);
          this.loadLocalitiesAndState();
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

    this.api
      .logout()
      .pipe(
        catchError((err: HttpErrorResponse) => {
          this.showActionFeedback(this.formatActionError(err));
          return of(null);
        })
      )
      .subscribe((res) => {
        if (res === null) return;
        this.auth.set({
          authenticated: false,
          username: 'observador',
          role: 'observer',
          operable_sites: [],
        });
        this.state.set(null);
        this.dismissActionFeedback();
        this.errorMessage.set('Sesión cerrada. Inicia sesión para continuar.');
      });
  }

  startSession(): void {
    const s = this.state();
    if (!s) return;
    if (this.isMockMode()) {
      this.setMockState('encendida');
      return;
    }
    this.runAction(this.api.startSession(s.site.slug));
  }

  play(): void {
    const s = this.state();
    if (!s) return;
    if (this.isMockMode()) {
      this.state.set({ ...s, session: { ...s.session, playing: true } });
      return;
    }
    this.runAction(this.api.play(s.session.id));
  }

  pause(): void {
    const s = this.state();
    if (!s) return;
    if (this.isMockMode()) {
      this.state.set({ ...s, session: { ...s.session, playing: false } });
      return;
    }
    this.runAction(this.api.pause(s.session.id));
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
    this.runAction(this.api.nextBand(s.session.id));
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
        const targetCurrent =
          z.kind === 'dc_load' ? this.getBenchKnobCurrent(z) : z.current_a;
        const currentA = nextOn ? targetCurrent : 0;
        const powerW = nextOn
          ? z.dimmable
            ? Number(((80 * (z.intensity_pct ?? 75)) / 100).toFixed(2))
            : z.kind === 'dc_load'
              ? Number((z.voltage_v * currentA).toFixed(2))
              : 160
          : 0;
        const active = nextOn && powerW > 0;
        return {
          ...z,
          on: nextOn,
          current_a: currentA,
          setpoint_current_a: z.kind === 'dc_load' ? targetCurrent : null,
          power_w: powerW,
          indicator: {
            led: (active ? 'green' : 'off') as 'green' | 'off',
            label: active
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
      this.applyState({
        ...s,
        zones: nextZones,
        session: {
          ...s.session,
          total_power_w: totalPower,
          time_to_threshold_s:
            totalPower > 0 ? Math.round((s.session.remaining_wh * 3600) / totalPower) : null,
          status_label: this.computeMockStatusLabel(s, totalPower),
        },
      });
      return;
    }

    this.runAction(this.api.updateZone(s.session.id, zoneSlug, { on: nextOn }));
  }

  private scheduleSliderCommit(
    key: string,
    value: number,
    immediate: boolean,
    sendFn: () => void
  ): void {
    const existing = this.sliderTimers.get(key);
    if (existing) {
      clearTimeout(existing);
      this.sliderTimers.delete(key);
    }

    const commit = () => {
      this.sliderTimers.delete(key);
      if (this.lastSentSliderValue.get(key) === value) {
        return;
      }
      this.lastSentSliderValue.set(key, value);
      sendFn();
    };

    if (immediate) {
      commit();
    } else {
      this.lastSentSliderValue.delete(key);
      this.sliderTimers.set(key, setTimeout(commit, SLIDER_DEBOUNCE_MS));
    }
  }

  setBenchCurrent(zoneSlug: string, currentA: number, immediate = false): void {
    const s = this.state();
    if (!s) return;
    this.benchCurrentRemembered.update((prev) => ({
      ...prev,
      [this.knobKey(s.site.slug, zoneSlug)]: currentA,
    }));

    const nextZones = s.zones.map((z) => {
      if (z.slug !== zoneSlug) return z;
      const powerW = z.on ? Number((z.voltage_v * currentA).toFixed(2)) : 0;
      const active = z.on && powerW > 0;
      return {
        ...z,
        current_a: z.on ? currentA : 0,
        setpoint_current_a: currentA,
        power_w: powerW,
        indicator: {
          led: (active ? 'green' : 'off') as 'green' | 'off',
          label: active ? 'Carga habilitada' : 'Carga deshabilitada',
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
        status_label: this.computeMockStatusLabel(s, totalPower),
      },
    });

    if (this.isMockMode()) {
      return;
    }

    const sessionId = s.session.id;
    this.scheduleSliderCommit(`bench:${zoneSlug}`, currentA, immediate, () => {
      this.runAction(this.api.updateZone(sessionId, zoneSlug, { current_a: currentA }));
    });
  }

  setZoneIntensity(zoneSlug: string, intensityPct: number, immediate = false): void {
    const s = this.state();
    if (!s) return;

    const nextZones = s.zones.map((z) => {
      if (z.slug !== zoneSlug) return z;
      const powerW = z.on ? Number(((80 * intensityPct) / 100).toFixed(2)) : 0;
      const active = z.on && powerW > 0;
      return {
        ...z,
        intensity_pct: intensityPct,
        power_w: powerW,
        indicator: {
          led: (active ? 'green' : 'off') as 'green' | 'off',
          label: active ? 'Encendida' : 'Apagada',
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
        status_label: this.computeMockStatusLabel(s, totalPower),
      },
    });

    if (this.isMockMode()) {
      return;
    }

    const sessionId = s.session.id;
    this.scheduleSliderCommit(`dim:${zoneSlug}`, intensityPct, immediate, () => {
      this.runAction(this.api.updateZone(sessionId, zoneSlug, { intensity_pct: intensityPct }));
    });
  }

  toggleConnection(): void {
    const s = this.state();
    if (!s) return;
    const nextConn = !s.session.connected;
    if (this.isMockMode()) {
      this.setMockState(nextConn ? 'encendida' : 'sin_conexion');
      return;
    }
    this.runAction(this.api.setConnection(s.session.id, nextConn));
  }

  ackAlert(alertId: string): void {
    const s = this.state();
    if (!s) return;
    if (this.isMockMode()) {
      this.applyState({
        ...s,
        alerts: s.alerts.map((a) =>
          a.id === alertId ? { ...a, acknowledged: true } : a
        ),
      });
      return;
    }
    this.runAction(this.api.ackAlert(s.session.id, alertId));
  }
}
