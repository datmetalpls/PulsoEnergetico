import {
  Component,
  ElementRef,
  HostListener,
  OnDestroy,
  OnInit,
  ViewChild,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { EnergyChartsComponent } from './components/energy-charts.component';
import {
  BandKey,
  ComparisonResponse,
  MockStateKey,
  StateResponse,
  ZoneState,
} from './models/pulso.models';
import { AudioAlertService } from './services/audio-alert.service';
import { PulsoStoreService } from './services/pulso-store.service';
import {
  formatCurrent,
  formatDecimal,
  formatDuration,
  formatEnergy,
  formatPower,
  formatVoltage,
} from './utils/format';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [FormsModule, EnergyChartsComponent],
  templateUrl: './app.component.html',
})
export class AppComponent implements OnInit, OnDestroy {
  readonly store = inject(PulsoStoreService);
  readonly audio = inject(AudioAlertService);

  @ViewChild('menuToggleBtn') private menuToggleBtn?: ElementRef<HTMLButtonElement>;
  @ViewChild('menuDrawer') private menuDrawer?: ElementRef<HTMLElement>;

  readonly showLogin = signal(false);
  readonly menuOpen = signal(false);
  readonly loginUsername = signal('operador_cuenca');
  readonly loginPassword = signal('');

  readonly isLocalDemoHost =
    typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

  readonly mockStates: Array<{ key: MockStateKey; label: string }> = [
    { key: 'inicial', label: '1. Inicial' },
    { key: 'apagada', label: '2. Carga apagada' },
    { key: 'encendida', label: '3. Carga encendida' },
    { key: 'umbral', label: '4. Umbral alcanzado' },
    { key: 'sin_conexion', label: '5. Conexión interrumpida' },
  ];

  readonly bands: Array<{ key: BandKey; label: string }> = [
    { key: 'day', label: 'Día' },
    { key: 'afternoon', label: 'Tarde' },
    { key: 'night', label: 'Noche' },
  ];

  readonly themeClass = computed(() => {
    const band = this.store.currentBand();
    return `theme-${band}`;
  });

  readonly progressPct = computed(() => {
    const s = this.store.state();
    if (!s || s.session.threshold_wh <= 0) return 0;
    return Math.min(100, Math.round((s.session.energy_wh / s.session.threshold_wh) * 100));
  });

  readonly anyZoneOn = computed(() => {
    const s = this.store.state();
    return s ? s.zones.some((z) => z.on) : false;
  });

  readonly guideStep = computed<1 | 2 | 3 | 'done'>(() => {
    const s = this.store.state();
    if (!s) return 'done';
    if (s.session.status === 'idle' || s.session.status === 'closed' || s.session.alert_fired) {
      return 1;
    }
    if (!s.zones.some((z) => z.on)) {
      return 2;
    }
    if (!s.session.playing) {
      return 3;
    }
    return 'done';
  });

  readonly primaryStepLabel = computed(() => {
    switch (this.guideStep()) {
      case 1:
        return '1 Iniciar ensayo';
      case 2:
        return '2 Encender';
      case 3:
        return '3 Reproducir';
      case 'done':
        return 'Pausar';
    }
  });

  ngOnInit(): void {
    this.store.init();
  }

  ngOnDestroy(): void {
    this.store.destroy();
  }

  onPrimaryHeaderAction(): void {
    const step = this.guideStep();
    if (step === 1) {
      this.store.startSession();
    } else if (step === 2) {
      this.activateFirstOffZone();
    } else if (step === 3) {
      this.store.play();
    } else {
      this.store.pause();
    }
  }

  openMenu(): void {
    this.menuOpen.set(true);
    setTimeout(() => {
      const firstFocusable = this.getDrawerFocusables()[0];
      firstFocusable?.focus();
    }, 0);
  }

  closeMenu(restoreFocus = true): void {
    if (!this.menuOpen()) return;
    this.menuOpen.set(false);
    if (restoreFocus) {
      setTimeout(() => {
        this.menuToggleBtn?.nativeElement.focus();
      }, 0);
    }
  }

  toggleMenu(): void {
    if (this.menuOpen()) {
      this.closeMenu(true);
    } else {
      this.openMenu();
    }
  }

  @HostListener('document:keydown', ['$event'])
  onDocumentKeydown(event: KeyboardEvent): void {
    if (!this.menuOpen()) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      this.closeMenu(true);
      return;
    }
    if (event.key === 'Tab') {
      const focusables = this.getDrawerFocusables();
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }

  private getDrawerFocusables(): HTMLElement[] {
    const root = this.menuDrawer?.nativeElement;
    if (!root) return [];
    return Array.from(
      root.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    );
  }

  onMenuAction(
    action: 'start' | 'nextBand' | 'pause' | 'connection' | 'presentation' | 'logout' | 'login'
  ): void {
    this.closeMenu(false);
    switch (action) {
      case 'start':
        this.store.startSession();
        break;
      case 'nextBand':
        this.store.nextBand();
        break;
      case 'pause':
        this.store.pause();
        break;
      case 'connection':
        this.store.toggleConnection();
        break;
      case 'presentation':
        this.store.openPresentationMode();
        break;
      case 'logout':
        this.store.logout();
        break;
      case 'login':
        this.showLogin.set(true);
        break;
    }
  }

  onLocalityChange(slug: string): void {
    this.store.selectLocality(slug);
  }

  onSiteChange(slug: string): void {
    this.store.selectSite(slug);
  }

  onLoginSubmit(): void {
    this.store.login(this.loginUsername(), this.loginPassword());
    this.showLogin.set(false);
  }

  loginAsDemoOperator(): void {
    if (!this.isLocalDemoHost) return;
    this.loginUsername.set('operador_demo');
    this.loginPassword.set('Demo-2026');
    this.onLoginSubmit();
  }

  activateFirstOffZone(): void {
    const s = this.store.state();
    if (!s) return;
    const firstOff = s.zones.find((z) => !z.on);
    if (firstOff) {
      this.store.setZoneOn(firstOff.slug, true);
    }
  }

  onBenchCurrentInput(zoneSlug: string, event: Event): void {
    const val = Number((event.target as HTMLInputElement).value);
    if (Number.isFinite(val)) {
      this.store.setBenchCurrent(zoneSlug, val, false);
    }
  }

  onBenchCurrentChange(zoneSlug: string, event: Event): void {
    const val = Number((event.target as HTMLInputElement).value);
    if (Number.isFinite(val)) {
      this.store.setBenchCurrent(zoneSlug, val, true);
    }
  }

  onIntensityInput(zoneSlug: string, event: Event): void {
    const val = Number((event.target as HTMLInputElement).value);
    if (Number.isFinite(val)) {
      this.store.setZoneIntensity(zoneSlug, val, false);
    }
  }

  onIntensityChange(zoneSlug: string, event: Event): void {
    const val = Number((event.target as HTMLInputElement).value);
    if (Number.isFinite(val)) {
      this.store.setZoneIntensity(zoneSlug, val, true);
    }
  }

  toggleSound(): void {
    if (this.audio.soundEnabled()) {
      this.audio.disableSound();
    } else {
      this.audio.enableSound();
    }
  }

  speedScaleDetail(s: StateResponse): string {
    if (s.session.speed === 60) {
      return '1 s real = 1 min simulado';
    }
    if (s.session.speed === 300) {
      return '1 s real = 5 min simulados';
    }
    return `1 s real = ${s.session.speed} s simulados`;
  }

  comparisonRunEnergy(cmp: ComparisonResponse, key: 'A' | 'B'): number {
    const found = cmp.runs.find((r) => r.key === key);
    if (found) return found.energy_wh;
    return key === 'A' ? (cmp.runs[0]?.energy_wh ?? 0) : (cmp.runs[1]?.energy_wh ?? 0);
  }

  roundSeconds(val: number): number {
    return Math.round(val);
  }

  sessionStatusText(s: StateResponse): string {
    if (s.session.total_power_w <= 0) {
      if (s.session.status === 'idle') {
        return 'Ensayo sin iniciar · Consumo detenido';
      }
      if (s.session.alert_fired) {
        return 'Umbral alcanzado · Consumo detenido';
      }
      if (!s.session.connected) {
        return 'Conexión interrumpida · Consumo detenido';
      }
      return 'Consumo detenido';
    }
    if (!s.session.connected) {
      return 'Conexión interrumpida';
    }
    if (s.session.alert_fired) {
      return 'Umbral alcanzado';
    }
    return 'Consumiendo';
  }

  benchKnobAriaText(zone: ZoneState): string {
    const val = this.fmtCurrent(this.store.getBenchKnobCurrent(zone));
    return zone.on ? `${val}, carga habilitada` : `${val}, preajuste con carga apagada`;
  }

  intensityAriaText(zone: ZoneState): string {
    const pct = zone.intensity_pct ?? 0;
    return zone.on ? `${pct} por ciento` : `${pct} por ciento, preajuste con zona apagada`;
  }

  // Formatting helpers exposed to template
  fmtPower = formatPower;
  fmtEnergy = formatEnergy;
  fmtCurrent = formatCurrent;
  fmtVoltage = formatVoltage;
  fmtDuration = formatDuration;
  fmtDecimal = formatDecimal;
}
