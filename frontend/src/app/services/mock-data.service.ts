import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin, map, Observable, of, tap } from 'rxjs';
import {
  BandKey,
  ComparisonResponse,
  LocalityWithSites,
  MockStateKey,
  ReportResponse,
  StateResponse,
} from '../models/pulso.models';

const BAND_META: Record<BandKey, { label: string; baseClock: string }> = {
  day: { label: 'Día', baseClock: '08:00:18' },
  afternoon: { label: 'Tarde', baseClock: '15:20:18' },
  night: { label: 'Noche', baseClock: '20:10:18' },
};

const LOCALITIES_FIXTURE: LocalityWithSites[] = [
  {
    slug: 'cuenca',
    name: 'Cuenca',
    country: 'Ecuador',
    timezone: 'America/Guayaquil',
    sites: [
      {
        slug: 'cuenca-banco',
        name: 'Banco de pruebas 5 V',
        kind: 'bench',
        fictitious: false,
        budget_kwh_day: null,
        sample_interval_s: 1,
      },
      {
        slug: 'cuenca-sede',
        name: 'Centro Comunitario Río Tomebamba (ficticio)',
        kind: 'venue',
        fictitious: true,
        budget_kwh_day: 0.6,
        sample_interval_s: 60,
      },
    ],
  },
  {
    slug: 'puente-alto',
    name: 'Puente Alto',
    country: 'Chile',
    timezone: 'America/Santiago',
    sites: [
      {
        slug: 'puente-alto-banco',
        name: 'Banco de pruebas 5 V',
        kind: 'bench',
        fictitious: false,
        budget_kwh_day: null,
        sample_interval_s: 1,
      },
      {
        slug: 'puente-alto-sede',
        name: 'Sede Vecinal Los Andes (ficticia)',
        kind: 'venue',
        fictitious: true,
        budget_kwh_day: 0.6,
        sample_interval_s: 60,
      },
    ],
  },
];

@Injectable({ providedIn: 'root' })
export class MockDataService {
  private readonly http = inject(HttpClient);
  private benchBase: StateResponse | null = null;
  private venueBase: StateResponse | null = null;
  private reportBase: ReportResponse | null = null;

  loadFixtures(): Observable<void> {
    if (this.benchBase && this.venueBase && this.reportBase) {
      return of(undefined);
    }
    return forkJoin({
      bench: this.http.get<StateResponse>('assets/mock/state.example.json'),
      venue: this.http.get<StateResponse>('assets/mock/state.venue.example.json'),
      report: this.http.get<ReportResponse>('assets/mock/report.example.json'),
    }).pipe(
      tap(({ bench, venue, report }) => {
        this.benchBase = bench;
        this.venueBase = venue;
        this.reportBase = report;
      }),
      map(() => undefined)
    );
  }

  getLocalities(): LocalityWithSites[] {
    return structuredClone(LOCALITIES_FIXTURE);
  }

  buildState(
    siteSlug: string,
    mockState: MockStateKey,
    band: BandKey,
    role: 'operator' | 'observer'
  ): StateResponse {
    const isVenue = siteSlug.endsWith('-sede');
    const base = structuredClone(isVenue ? this.venueBase! : this.benchBase!);

    const loc = LOCALITIES_FIXTURE.find((l) =>
      l.sites.some((s) => s.slug === siteSlug)
    ) ?? LOCALITIES_FIXTURE[0];
    const site = loc.sites.find((s) => s.slug === siteSlug) ?? loc.sites[0];

    base.locality = {
      slug: loc.slug,
      name: loc.name,
      country: loc.country,
      timezone: loc.timezone,
    };
    base.site = structuredClone(site);
    base.permissions = {
      role,
      can_operate: role === 'operator',
    };
    base.session.band = band;
    base.session.band_label = BAND_META[band].label;
    base.session.scenario_clock = BAND_META[band].baseClock;

    if (isVenue) {
      const voltage = loc.slug === 'cuenca' ? 120.0 : 220.0;
      for (const z of base.zones) {
        z.voltage_v = voltage;
        z.current_a = z.on ? Number((z.power_w / voltage).toFixed(3)) : 0;
      }
    }

    switch (mockState) {
      case 'inicial': {
        base.session.status = 'idle';
        base.session.playing = false;
        base.session.elapsed_s = 0;
        base.session.energy_wh = 0;
        base.session.remaining_wh = base.session.threshold_wh;
        base.session.total_power_w = 0;
        base.session.time_to_threshold_s = null;
        base.session.status_label = 'Ensayo sin iniciar';
        base.session.alert_fired = false;
        base.session.scenario_clock =
          band === 'day' ? '08:00:00' : band === 'afternoon' ? '14:00:00' : '19:00:00';
        base.alerts = [];
        base.gaps = [];
        for (const z of base.zones) {
          z.on = false;
          z.current_a = 0;
          z.setpoint_current_a = z.kind === 'dc_load' ? 0.4 : null;
          z.power_w = 0;
          z.energy_wh = 0;
          z.on_seconds = 0;
          z.indicator = { led: 'off', label: 'Carga deshabilitada' };
        }
        for (const key of Object.keys(base.series)) {
          base.series[key] = [{ t_s: 0, power_w: 0, energy_wh: 0 }];
        }
        break;
      }

      case 'apagada': {
        base.session.playing = true;
        base.session.total_power_w = 0;
        base.session.time_to_threshold_s = null;
        base.session.status_label = 'Consumo detenido';
        base.session.alert_fired = false;
        base.alerts = [];
        if (!isVenue) {
          base.session.elapsed_s = 24;
          base.session.energy_wh = 0.01;
          base.session.remaining_wh = 0.01;
          base.zones[0].on = false;
          base.zones[0].current_a = 0;
          base.zones[0].setpoint_current_a = 0.4;
          base.zones[0].power_w = 0;
          base.zones[0].indicator = { led: 'off', label: 'Carga deshabilitada' };
          const flat = [
            { t_s: 0, power_w: 2.0, energy_wh: 0.0 },
            { t_s: 9, power_w: 2.0, energy_wh: 0.005 },
            { t_s: 18, power_w: 2.0, energy_wh: 0.01 },
            { t_s: 18, power_w: 0.0, energy_wh: 0.01 },
            { t_s: 24, power_w: 0.0, energy_wh: 0.01 },
          ];
          base.series['carga-5v'] = flat;
          base.series['total'] = structuredClone(flat);
        } else {
          base.session.elapsed_s = 5400;
          base.session.energy_wh = 245.0;
          base.session.remaining_wh = 355.0;
          for (const z of base.zones) {
            z.on = false;
            z.current_a = 0;
            z.power_w = 0;
            z.indicator = { led: 'off', label: 'Apagada' };
          }
          base.series['total'] = [
            { t_s: 0, power_w: 160, energy_wh: 0 },
            { t_s: 3600, power_w: 160, energy_wh: 245 },
            { t_s: 5400, power_w: 0, energy_wh: 245 },
          ];
        }
        break;
      }

      case 'encendida': {
        base.session.playing = true;
        base.session.alert_fired = false;
        base.alerts = [];
        if (isVenue) {
          base.session.elapsed_s = 3600;
          base.session.energy_wh = 220.0;
          base.session.remaining_wh = 380.0;
          base.session.total_power_w = 220.0;
          base.session.time_to_threshold_s = 6218;
          base.session.status_label = 'Consumiendo';
          base.zones[0].on = true;
          base.zones[0].power_w = 160.0;
          base.zones[0].energy_wh = 160.0;
          base.zones[0].indicator = { led: 'green', label: 'Encendida' };
          base.zones[1].on = true;
          base.zones[1].intensity_pct = 75;
          base.zones[1].power_w = 60.0;
          base.zones[1].energy_wh = 60.0;
          base.zones[1].indicator = { led: 'green', label: 'Encendida' };
          base.gaps = [];
          base.series['salon-principal'] = [
            { t_s: 0, power_w: 160, energy_wh: 0 },
            { t_s: 3600, power_w: 160, energy_wh: 160 },
          ];
          base.series['sala-reuniones'] = [
            { t_s: 0, power_w: 60, energy_wh: 0 },
            { t_s: 3600, power_w: 60, energy_wh: 60 },
          ];
          base.series['total'] = [
            { t_s: 0, power_w: 220, energy_wh: 0 },
            { t_s: 3600, power_w: 220, energy_wh: 220 },
          ];
        }
        break;
      }

      case 'umbral': {
        base.session.alert_fired = true;
        base.session.status_label = 'Presupuesto alcanzado';
        if (!isVenue) {
          base.session.elapsed_s = 36;
          base.session.energy_wh = 0.02;
          base.session.remaining_wh = 0.0;
          base.session.time_to_threshold_s = 0;
          base.zones[0].energy_wh = 0.02;
          base.zones[0].on_seconds = 36;
          base.alerts = [
            {
              id: `alert-bench-${siteSlug}`,
              kind: 'threshold',
              t_s: 36,
              energy_wh: 0.02,
              threshold_wh: 0.02,
              channel: 'browser',
              channel_label: 'Aviso del navegador (imita el buzzer, 0,8 s, una vez)',
              message: 'Límite alcanzado: 0,0200 Wh en el banco de pruebas',
              acknowledged: false,
            },
          ];
          const series = [
            { t_s: 0, power_w: 2.0, energy_wh: 0.0 },
            { t_s: 12, power_w: 2.0, energy_wh: 0.006667 },
            { t_s: 24, power_w: 2.0, energy_wh: 0.013333 },
            { t_s: 36, power_w: 2.0, energy_wh: 0.02 },
          ];
          base.series['carga-5v'] = series;
          base.series['total'] = structuredClone(series);
        }
        break;
      }

      case 'sin_conexion': {
        base.session.connected = false;
        base.session.status_label = 'Conexión interrumpida';
        base.session.alert_fired = false;
        base.alerts = [];
        if (!isVenue) {
          base.session.elapsed_s = 28;
          base.session.energy_wh = 0.01;
          base.session.remaining_wh = 0.01;
          base.gaps = [
            {
              zone: 'carga-5v',
              from_t_s: 18,
              to_t_s: 28,
              duration_s: 10,
              label: 'Sin datos: conexión interrumpida',
            },
          ];
          const series = [
            { t_s: 0, power_w: 2.0, energy_wh: 0.0 },
            { t_s: 9, power_w: 2.0, energy_wh: 0.005 },
            { t_s: 18, power_w: 2.0, energy_wh: 0.01 },
            { t_s: 28, power_w: 2.0, energy_wh: 0.01 },
          ];
          base.series['carga-5v'] = series;
          base.series['total'] = structuredClone(series);
        } else {
          base.gaps = [
            {
              zone: 'salon-principal',
              from_t_s: 3600,
              to_t_s: 4200,
              duration_s: 600,
              label: 'Sin datos: conexión interrumpida',
            },
          ];
        }
        break;
      }

      case 'reporte': {
        base.session.playing = false;
        base.session.total_power_w = 0;
        base.session.time_to_threshold_s = null;
        base.session.alert_fired = true;
        base.session.status_label = 'Reporte disponible';
        if (!isVenue) {
          base.session.elapsed_s = 46;
          base.session.energy_wh = 0.02;
          base.session.remaining_wh = 0;
          base.zones[0].on = false;
          base.zones[0].power_w = 0;
          base.zones[0].current_a = 0;
          base.zones[0].energy_wh = 0.02;
          base.zones[0].on_seconds = 36;
          base.zones[0].indicator = { led: 'off', label: 'Carga deshabilitada' };
          base.alerts = [
            {
              id: `alert-report-${siteSlug}`,
              kind: 'threshold',
              t_s: 36,
              energy_wh: 0.02,
              threshold_wh: 0.02,
              channel: 'browser',
              channel_label: 'Aviso del navegador (imita el buzzer, 0,8 s, una vez)',
              message: 'Límite alcanzado: 0,0200 Wh',
              acknowledged: true,
            },
          ];
          const series = [
            { t_s: 0, power_w: 2.0, energy_wh: 0.0 },
            { t_s: 18, power_w: 2.0, energy_wh: 0.01 },
            { t_s: 36, power_w: 2.0, energy_wh: 0.02 },
            { t_s: 46, power_w: 0.0, energy_wh: 0.02 },
          ];
          base.series['carga-5v'] = series;
          base.series['total'] = structuredClone(series);
        }
        break;
      }
    }

    return base;
  }

  buildReport(state: StateResponse): ReportResponse {
    const base = structuredClone(this.reportBase!);
    base.session_id = state.session.id;
    base.site = state.site.name;
    base.locality = state.locality.name;
    if (state.site.kind === 'venue') {
      const kwh = (state.session.energy_wh / 1000).toFixed(3).replace('.', ',');
      const thr = (state.session.threshold_wh / 1000).toFixed(3).replace('.', ',');
      base.text = `Resumen de ${state.site.name}, ${state.locality.name}. Datos simulados. Energía acumulada: ${kwh} kilovatios hora frente al presupuesto de ${thr} kilovatios hora. Potencia actual: ${state.session.total_power_w.toFixed(0)} vatios.`;
      base.discord_preview.content = `⚡ Pulso Energético · ${state.site.name} (${state.locality.name}) — acumulado ${kwh} kWh de ${thr} kWh. [Datos simulados]`;
    }
    return base;
  }

  buildComparison(siteSlug: string): ComparisonResponse {
    return {
      duration_s: 21600,
      runs: [
        {
          key: 'always_on',
          label: 'Sala encendida',
          energy_wh: 1320,
          zones: [
            { zone: 'salon-principal', energy_wh: 960, on_seconds: 21600 },
            { zone: 'sala-reuniones', energy_wh: 360, on_seconds: 21600 },
          ],
        },
        {
          key: 'turned_off',
          label: 'Sala apagada al terminar la reunión',
          energy_wh: 1140,
          zones: [
            { zone: 'salon-principal', energy_wh: 960, on_seconds: 21600 },
            { zone: 'sala-reuniones', energy_wh: 180, on_seconds: 10800 },
          ],
        },
      ],
      difference_wh: 180,
      salon_on_seconds: 21600,
      note: `Datos de demostración (${siteSlug})`,
    };
  }
}
