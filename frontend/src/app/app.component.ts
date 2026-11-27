import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { EnergyChartsComponent } from './components/energy-charts.component';
import { BandKey, MockStateKey } from './models/pulso.models';
import { AudioAlertService } from './services/audio-alert.service';
import { PulsoStoreService } from './services/pulso-store.service';
import { SpeechReportService } from './services/speech-report.service';
import {
  formatCurrent,
  formatDecimal,
  formatDuration,
  formatEnergy,
  formatPower,
  formatVoltage,
  sourceLabel,
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
  readonly speech = inject(SpeechReportService);

  readonly showLogin = signal(false);
  readonly loginUsername = signal('operador_cuenca');
  readonly loginPassword = signal('');

  readonly mockStates: Array<{ key: MockStateKey; label: string }> = [
    { key: 'inicial', label: '1. Inicial' },
    { key: 'apagada', label: '2. Carga apagada' },
    { key: 'encendida', label: '3. Carga encendida' },
    { key: 'umbral', label: '4. Umbral alcanzado' },
    { key: 'sin_conexion', label: '5. Conexión interrumpida' },
    { key: 'reporte', label: '6. Reporte disponible' },
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

  listenReport(): void {
    const existing = this.store.report();
    if (existing) {
      this.speech.speak(existing.text);
      return;
    }
    this.store.loadReport();
    setTimeout(() => {
      const rep = this.store.report();
      if (rep) {
        this.speech.speak(rep.text);
      }
    }, 150);
  }

  // Formatting helpers exposed to template
  fmtPower = formatPower;
  fmtEnergy = formatEnergy;
  fmtCurrent = formatCurrent;
  fmtVoltage = formatVoltage;
  fmtDuration = formatDuration;
  fmtDecimal = formatDecimal;
  fmtSource = sourceLabel;
}
