import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { EnergyChartsComponent } from './components/energy-charts.component';
import { BandKey, MockStateKey, StateResponse, ZoneState } from './models/pulso.models';
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

  readonly showLogin = signal(false);
  readonly loginUsername = signal('operador_cuenca');
  readonly loginPassword = signal('');

  readonly mockStates: Array<{ key: MockStateKey; label: string }> = [
    { key: 'inicial', label: '1. Inicial' },
    { key: 'apagada', label: '2. Carga apagada' },
    { key: 'encendida', label: '3. Carga encendida' },
    { key: 'umbral', label: '4. Umbral alcanzado' },
    { key: 'sin_conexion', label: '5. Conexión interrumpida' },
  ];

  readonly bands: Array<{ key: BandKey; label: string; icon: string }> = [
    { key: 'day', label: 'Día', icon: '☀' },
    { key: 'afternoon', label: 'Tarde', icon: '🌇' },
    { key: 'night', label: 'Noche', icon: '🌙' },
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

  ngOnInit(): void {
    this.store.init();
  }

  ngOnDestroy(): void {
    this.store.destroy();
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

  onBenchCurrentInput(zoneSlug: string, event: Event): void {
    const val = Number((event.target as HTMLInputElement).value);
    if (Number.isFinite(val)) {
      this.store.setBenchCurrent(zoneSlug, val);
    }
  }

  onIntensityInput(zoneSlug: string, event: Event): void {
    const val = Number((event.target as HTMLInputElement).value);
    if (Number.isFinite(val)) {
      this.store.setZoneIntensity(zoneSlug, val);
    }
  }

  toggleSound(): void {
    if (this.audio.soundEnabled()) {
      this.audio.disableSound();
    } else {
      this.audio.enableSound();
    }
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
