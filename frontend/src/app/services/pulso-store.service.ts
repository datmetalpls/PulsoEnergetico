import { HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, effect, inject, signal } from '@angular/core';
import { Observable, catchError, concatMap, of } from 'rxjs';
import {
  AuthMeResponse,
  BandKey,
  ComparisonResponse,
  LocalityWithSites,
  MockStateKey,
  ReportResponse,
  StateResponse,
  ZoneState,
} from '../models/pulso.models';
import { AudioAlertService } from './audio-alert.service';
import { MockDataService } from './mock-data.service';
import { PulsoApiService } from './pulso-api.service';

const DEFAULT_BENCH_CURRENT_A = 0.4;
const SLIDER_DEBOUNCE_MS = 250;
const ACTION_FEEDBACK_MS = 6000;
const STORAGE_LOCALITY_KEY = 'pulso_selected_locality';
const STORAGE_SITE_KEY = 'pulso_selected_site';
const STORAGE_PRESENTATION_KEY = 'pulso_presentation_state';
const STORAGE_RESTORE_BUDGET_KEY = 'pulso_restore_budget_site';

export type PresentationStep = 0 | 1 | 2 | 3;

interface SavedPresentationState {
  active: boolean;
  siteSlug: string;
  step: PresentationStep;
  sessionId: string | null;
  startedAtMs: number | null;
  alertElapsedMs: number | null;
}

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
  readonly selectedLocalitySlug = signal<string>(
    this.readSessionString(STORAGE_LOCALITY_KEY) || 'cuenca'
  );
  readonly selectedSiteSlug = signal<string>(
    this.readSessionString(STORAGE_SITE_KEY) || 'cuenca-banco'
  );

  readonly state = signal<StateResponse | null>(null);
  readonly comparison = signal<ComparisonResponse | null>(null);
  readonly sessionReport = signal<ReportResponse | null>(null);

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

  // Guided Presentation Mode state (persisted in sessionStorage across refresh)
  readonly presentationActive = signal(false);
  readonly presentationStep = signal<PresentationStep>(0);
  readonly presentationSiteSlug = signal<string | null>(null);
  readonly presentationSessionId = signal<string | null>(null);
  readonly presentationStartedAtMs = signal<number | null>(null);
  readonly presentationAlertElapsedMs = signal<number | null>(null);
  readonly presentationBusy = signal(false);
  readonly presentationRestorePromptSite = signal<string | null>(
    this.readSessionString(STORAGE_RESTORE_BUDGET_KEY)
  );

  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private feedbackTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly sliderTimers = new Map<string, ReturnType<typeof setTimeout>>();
  private readonly lastSentSliderValue = new Map<string, number>();
  private comparisonFetchedForSite: string | null = null;
  private reportFetchedForSession: string | null = null;

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
    this.restorePresentationFromStorage();

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

  private readSessionString(key: string): string | null {
    if (typeof sessionStorage === 'undefined') return null;
    try {
      return sessionStorage.getItem(key);
    } catch {
      return null;
    }
  }

  private writeSessionString(key: string, value: string | null): void {
    if (typeof sessionStorage === 'undefined') return;
    try {
      if (value === null) {
        sessionStorage.removeItem(key);
      } else {
        sessionStorage.setItem(key, value);
      }
    } catch {
      // Ignore storage quota / private mode errors
    }
  }

  private persistPresentationToStorage(): void {
    if (!this.presentationActive()) {
      this.writeSessionString(STORAGE_PRESENTATION_KEY, null);
      return;
    }
    const payload: SavedPresentationState = {
      active: true,
      siteSlug: this.presentationSiteSlug() ?? this.selectedSiteSlug(),
      step: this.presentationStep(),
      sessionId: this.presentationSessionId(),
      startedAtMs: this.presentationStartedAtMs(),
      alertElapsedMs: this.presentationAlertElapsedMs(),
    };
    this.writeSessionString(STORAGE_PRESENTATION_KEY, JSON.stringify(payload));
  }

  private restorePresentationFromStorage(): void {
    if (this.isMockMode()) return;
    const raw = this.readSessionString(STORAGE_PRESENTATION_KEY);
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as SavedPresentationState;
      if (parsed && parsed.active && parsed.siteSlug) {
        this.presentationActive.set(true);
        this.presentationStep.set(parsed.step ?? 0);
        this.presentationSiteSlug.set(parsed.siteSlug);
        this.presentationSessionId.set(parsed.sessionId ?? null);
        this.presentationStartedAtMs.set(parsed.startedAtMs ?? null);
        this.presentationAlertElapsedMs.set(parsed.alertElapsedMs ?? null);
        this.selectedSiteSlug.set(parsed.siteSlug);
        if (parsed.siteSlug.startsWith('puente-alto')) {
          this.selectedLocalitySlug.set('puente-alto');
        } else if (parsed.siteSlug.startsWith('cuenca')) {
          this.selectedLocalitySlug.set('cuenca');
        }
      }
    } catch {
      this.writeSessionString(STORAGE_PRESENTATION_KEY, null);
    }
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
    this.dismissActionFeedback();
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
          this.writeSessionString(STORAGE_LOCALITY_KEY, currentLoc.slug);
          if (currentLoc.sites.length > 0) {
            const currentSite =
              currentLoc.sites.find((s) => s.slug === this.selectedSiteSlug()) ??
              currentLoc.sites[0];
            this.selectedSiteSlug.set(currentSite.slug);
            this.writeSessionString(STORAGE_SITE_KEY, currentSite.slug);
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

    this.syncComparisonForSite(next);
    this.syncPresentationOnState(next);
  }

  private syncComparisonForSite(next: StateResponse): void {
    if (next.site.kind !== 'venue') {
      this.comparison.set(null);
      this.comparisonFetchedForSite = null;
      return;
    }
    if (this.comparisonFetchedForSite === next.site.slug && this.comparison() !== null) {
      return;
    }
    this.comparisonFetchedForSite = next.site.slug;
    if (this.isMockMode()) {
      this.comparison.set(this.mock.buildComparison(next.site.slug));
      return;
    }
    this.api
      .getComparison(next.site.slug)
      .pipe(catchError(() => of(null)))
      .subscribe((cmp) => {
        if (cmp && this.selectedSiteSlug() === next.site.slug) {
          this.comparison.set(cmp);
        }
      });
  }

  private syncPresentationOnState(next: StateResponse): void {
    if (!this.presentationActive()) return;

    if (this.presentationSiteSlug() !== next.site.slug || !next.permissions.can_operate) {
      this.clearPresentationState();
      return;
    }

    const expectedSession = this.presentationSessionId();
    if (this.presentationStep() >= 1 && expectedSession && next.session.id !== expectedSession) {
      // Session was replaced externally (e.g. acceptance script)
      this.clearPresentationState();
      return;
    }

    if (
      this.presentationStep() >= 1 &&
      next.session.alert_fired &&
      this.presentationStartedAtMs() !== null &&
      this.presentationAlertElapsedMs() === null
    ) {
      this.presentationAlertElapsedMs.set(Date.now() - this.presentationStartedAtMs()!);
      this.persistPresentationToStorage();
    }

    if (
      this.presentationStep() === 3 &&
      next.session.alert_fired &&
      this.reportFetchedForSession !== next.session.id
    ) {
      this.reportFetchedForSession = next.session.id;
      if (this.isMockMode()) {
        this.sessionReport.set(this.mock.buildReport(next));
      } else {
        this.api
          .getReport(next.session.id)
          .pipe(catchError(() => of(null)))
          .subscribe((rep) => {
            if (rep && this.state()?.session.id === next.session.id) {
              this.sessionReport.set(rep);
            }
          });
      }
    }
  }

  private clearPresentationState(): void {
    this.presentationActive.set(false);
    this.presentationStep.set(0);
    this.presentationSiteSlug.set(null);
    this.presentationSessionId.set(null);
    this.presentationStartedAtMs.set(null);
    this.presentationAlertElapsedMs.set(null);
    this.presentationBusy.set(false);
    this.sessionReport.set(null);
    this.reportFetchedForSession = null;
    this.persistPresentationToStorage();
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
    this.writeSessionString(STORAGE_LOCALITY_KEY, localitySlug);
    const loc = this.localities().find((l) => l.slug === localitySlug);
    if (loc && loc.sites.length > 0) {
      this.selectSite(loc.sites[0].slug);
    }
  }

  selectSite(siteSlug: string): void {
    this.selectedSiteSlug.set(siteSlug);
    this.writeSessionString(STORAGE_SITE_KEY, siteSlug);
    this.dismissActionFeedback();
    if (this.presentationActive() && this.presentationSiteSlug() !== siteSlug) {
      this.clearPresentationState();
    }
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
      this.clearPresentationState();
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
        this.clearPresentationState();
        this.state.set(null);
        this.comparison.set(null);
        this.comparisonFetchedForSite = null;
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
    this.setZoneOn(zoneSlug, !zone.on);
  }

  setZoneOn(zoneSlug: string, on: boolean): void {
    const s = this.state();
    if (!s) return;
    const zone = s.zones.find((z) => z.slug === zoneSlug);
    if (!zone) return;

    if (this.isMockMode()) {
      const nextZones = s.zones.map((z) => {
        if (z.slug !== zoneSlug) return z;
        const targetCurrent =
          z.kind === 'dc_load' ? this.getBenchKnobCurrent(z) : z.current_a;
        const currentA = on ? targetCurrent : 0;
        const powerW = on
          ? z.dimmable
            ? Number(((80 * (z.intensity_pct ?? 75)) / 100).toFixed(2))
            : z.kind === 'dc_load'
              ? Number((z.voltage_v * currentA).toFixed(2))
              : 160
          : 0;
        const active = on && powerW > 0;
        return {
          ...z,
          on,
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

    this.runAction(this.api.updateZone(s.session.id, zoneSlug, { on }));
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

  // --- Guided Presentation Mode ---

  openPresentationMode(): void {
    const s = this.state();
    if (!s || !s.permissions.can_operate || s.site.kind !== 'venue') return;
    this.presentationActive.set(true);
    this.presentationStep.set(0);
    this.presentationSiteSlug.set(s.site.slug);
    this.presentationSessionId.set(null);
    this.presentationStartedAtMs.set(null);
    this.presentationAlertElapsedMs.set(null);
    this.presentationRestorePromptSite.set(null);
    this.writeSessionString(STORAGE_RESTORE_BUDGET_KEY, null);
    this.sessionReport.set(null);
    this.reportFetchedForSession = null;
    this.persistPresentationToStorage();
  }

  advancePresentationStep(): void {
    const s = this.state();
    if (!s || !this.presentationActive() || this.presentationBusy()) return;
    const currentStep = this.presentationStep();
    if (currentStep >= 3) return;

    if (this.isMockMode()) {
      this.advanceMockPresentationStep(currentStep);
      return;
    }

    this.presentationBusy.set(true);
    const siteSlug = s.site.slug;

    if (currentStep === 0) {
      // Paso 1, Día: nuevo ensayo, presupuesto 0.10 kWh, encender salón y sala (100 %), Reproducir
      let createdSessionId = '';
      this.api
        .startSession(siteSlug)
        .pipe(
          concatMap((s1) => {
            createdSessionId = s1.session.id;
            return this.api.updateSiteBudget(siteSlug, 0.1);
          }),
          concatMap(() =>
            this.api.updateZone(createdSessionId, 'salon-principal', { on: true })
          ),
          concatMap(() =>
            this.api.updateZone(createdSessionId, 'sala-reuniones', {
              on: true,
              intensity_pct: 100,
            })
          ),
          concatMap(() => this.api.play(createdSessionId)),
          catchError((err: HttpErrorResponse) => {
            this.showActionFeedback(this.formatActionError(err));
            this.presentationBusy.set(false);
            return of(null);
          })
        )
        .subscribe((next) => {
          this.presentationBusy.set(false);
          if (!next) return;
          this.errorMessage.set(null);
          this.dismissActionFeedback();
          this.presentationStep.set(1);
          this.presentationSessionId.set(next.session.id);
          this.presentationStartedAtMs.set(Date.now());
          this.presentationAlertElapsedMs.set(null);
          this.persistPresentationToStorage();
          this.applyState(next);
        });
      return;
    }

    if (currentStep === 1) {
      // Paso 2, Tarde: siguiente franja + apagar sala de reuniones (240 W -> 160 W)
      const sessionId = s.session.id;
      this.api
        .nextBand(sessionId)
        .pipe(
          concatMap(() =>
            this.api.updateZone(sessionId, 'sala-reuniones', { on: false })
          ),
          catchError((err: HttpErrorResponse) => {
            this.showActionFeedback(this.formatActionError(err));
            this.presentationBusy.set(false);
            return of(null);
          })
        )
        .subscribe((next) => {
          this.presentationBusy.set(false);
          if (!next) return;
          this.errorMessage.set(null);
          this.dismissActionFeedback();
          this.presentationStep.set(2);
          this.persistPresentationToStorage();
          this.applyState(next);
        });
      return;
    }

    if (currentStep === 2) {
      // Paso 3, Noche: siguiente franja (explica la alerta; al dispararse muestra resumen y ahorro)
      this.api
        .nextBand(s.session.id)
        .pipe(
          catchError((err: HttpErrorResponse) => {
            this.showActionFeedback(this.formatActionError(err));
            this.presentationBusy.set(false);
            return of(null);
          })
        )
        .subscribe((next) => {
          this.presentationBusy.set(false);
          if (!next) return;
          this.errorMessage.set(null);
          this.dismissActionFeedback();
          this.presentationStep.set(3);
          this.persistPresentationToStorage();
          this.applyState(next);
        });
    }
  }

  private advanceMockPresentationStep(currentStep: PresentationStep): void {
    if (currentStep === 0) {
      this.mockBand.set('day');
      this.mockState.set('encendida');
      const built = this.mock.buildState(this.selectedSiteSlug(), 'encendida', 'day', 'operator');
      built.site.budget_kwh_day = 0.1;
      built.session.threshold_wh = 100;
      built.session.energy_wh = 12;
      built.session.remaining_wh = 88;
      built.session.total_power_w = 240;
      built.zones[0].on = true;
      built.zones[0].power_w = 160;
      built.zones[1].on = true;
      built.zones[1].intensity_pct = 100;
      built.zones[1].power_w = 80;
      this.presentationStep.set(1);
      this.presentationSessionId.set(built.session.id);
      this.presentationStartedAtMs.set(Date.now());
      this.applyState(built);
    } else if (currentStep === 1) {
      this.mockBand.set('afternoon');
      const built = this.mock.buildState(this.selectedSiteSlug(), 'encendida', 'afternoon', 'operator');
      built.site.budget_kwh_day = 0.1;
      built.session.threshold_wh = 100;
      built.session.energy_wh = 48;
      built.session.remaining_wh = 52;
      built.session.total_power_w = 160;
      built.zones[0].on = true;
      built.zones[0].power_w = 160;
      built.zones[1].on = false;
      built.zones[1].power_w = 0;
      built.zones[1].indicator = { led: 'off', label: 'Apagada' };
      this.presentationStep.set(2);
      this.applyState(built);
    } else if (currentStep === 2) {
      this.mockBand.set('night');
      const built = this.mock.buildState(this.selectedSiteSlug(), 'umbral', 'night', 'operator');
      built.site.budget_kwh_day = 0.1;
      built.session.threshold_wh = 100;
      built.session.energy_wh = 101.333;
      built.session.remaining_wh = 0;
      built.session.total_power_w = 160;
      built.session.alert_fired = true;
      this.presentationStep.set(3);
      this.applyState(built);
    }
  }

  exitPresentationMode(): void {
    const s = this.state();
    this.clearPresentationState();
    if (s && s.site.kind === 'venue' && s.site.budget_kwh_day !== null && Math.abs(s.site.budget_kwh_day - 0.6) > 0.001) {
      this.presentationRestorePromptSite.set(s.site.slug);
      this.writeSessionString(STORAGE_RESTORE_BUDGET_KEY, s.site.slug);
    }
    if (s && s.session.playing) {
      this.pause();
    }
  }

  restoreDefaultBudget(siteSlug?: string): void {
    const s = this.state();
    const targetSlug = siteSlug ?? this.presentationRestorePromptSite() ?? s?.site.slug;
    if (!targetSlug) return;
    if (this.isMockMode()) {
      if (s) {
        this.applyState({
          ...s,
          site: { ...s.site, budget_kwh_day: 0.6 },
          session: { ...s.session, threshold_wh: 600 },
        });
      }
      this.dismissRestorePrompt();
      return;
    }
    this.api
      .updateSiteBudget(targetSlug, 0.6)
      .pipe(
        catchError((err: HttpErrorResponse) => {
          this.showActionFeedback(this.formatActionError(err));
          return of(null);
        })
      )
      .subscribe((next) => {
        if (next) {
          this.dismissRestorePrompt();
          if (this.selectedSiteSlug() === next.site.slug) {
            this.applyState(next);
          }
          this.showActionFeedback('Presupuesto restaurado a 0,60 kWh.');
        }
      });
  }

  dismissRestorePrompt(): void {
    this.presentationRestorePromptSite.set(null);
    this.writeSessionString(STORAGE_RESTORE_BUDGET_KEY, null);
  }
}
