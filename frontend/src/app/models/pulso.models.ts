export type BandKey = 'day' | 'afternoon' | 'night';
export type SiteKind = 'bench' | 'venue';
export type MockStateKey =
  | 'inicial'
  | 'apagada'
  | 'encendida'
  | 'umbral'
  | 'sin_conexion'
  | 'reporte';

export interface LocalityInfo {
  slug: string;
  name: string;
  country: string;
  timezone: string;
}

export interface SiteInfo {
  slug: string;
  name: string;
  kind: SiteKind;
  fictitious: boolean;
  budget_kwh_day: number | null;
  sample_interval_s: number;
}

export interface LocalityWithSites extends LocalityInfo {
  sites: SiteInfo[];
}

export interface HardwareInfo {
  simulated_board: string;
  planned_board: string;
}

export interface PermissionsInfo {
  role: 'operator' | 'observer';
  can_operate: boolean;
}

export interface SessionInfo {
  id: string;
  status: 'running' | 'closed' | 'idle';
  started_at: string | null;
  playing: boolean;
  speed: number;
  connected: boolean;
  elapsed_s: number;
  scenario_clock: string;
  band: BandKey;
  band_label: string;
  threshold_wh: number;
  energy_wh: number;
  remaining_wh: number;
  total_power_w: number;
  time_to_threshold_s: number | null;
  status_label: string;
  alert_fired: boolean;
}

export interface ZoneIndicator {
  led: 'green' | 'off' | 'amber' | 'red';
  label: string;
}

export interface ZoneState {
  slug: string;
  name: string;
  kind: 'dc_load' | 'light';
  dimmable: boolean;
  simulated_control: boolean;
  on: boolean;
  indicator: ZoneIndicator;
  voltage_v: number;
  current_a: number;
  setpoint_current_a?: number | null;
  max_current_a: number | null;
  intensity_pct: number | null;
  power_w: number;
  energy_wh: number;
  on_seconds: number;
}

export interface AlertItem {
  id: string;
  kind: 'threshold';
  t_s: number;
  energy_wh: number;
  threshold_wh: number;
  channel: 'browser' | 'wokwi_buzzer';
  channel_label: string;
  message: string;
  acknowledged: boolean;
  /** v0.1.2 (aditivo): fecha de envío a Discord, o null. */
  discord_sent_at?: string | null;
}

/** v0.1.2 (aditivo): estado del webhook de Discord; nunca incluye la URL. */
export interface DiscordStatus {
  configured: boolean;
  last_sent_at: string | null;
  alert_sent?: boolean;
  report_sent?: boolean;
  sent?: boolean;
  label?: string;
}

export interface GapItem {
  zone: string;
  from_t_s: number;
  to_t_s: number;
  duration_s: number;
  label: string;
}

export interface SeriesPoint {
  t_s: number;
  power_w: number;
  energy_wh: number;
}

export interface ContextCard {
  label: string;
  unit: string;
  text: string;
}

export interface StateResponse {
  contract_version: string;
  data_label: string;
  server_time: string;
  locality: LocalityInfo;
  site: SiteInfo;
  sources_available: string[];
  active_source: string;
  hardware: HardwareInfo;
  permissions: PermissionsInfo;
  session: SessionInfo;
  zones: ZoneState[];
  alerts: AlertItem[];
  gaps: GapItem[];
  series: Record<string, SeriesPoint[]>;
  context_card: ContextCard | null;
  discord?: DiscordStatus;
}

export interface ReportResponse {
  session_id: string;
  site: string;
  locality: string;
  data_label: string;
  values: {
    elapsed_s: number;
    on_seconds: number;
    energy_wh: number;
    threshold_wh: number;
    power_w: number;
    alert_fired: boolean;
    alert_t_s: number | null;
  };
  text: string;
  discord?: DiscordStatus;
  discord_preview: {
    label: string;
    sent: boolean;
    content: string;
  };
}

export interface ComparisonRun {
  key: string;
  label: string;
  energy_wh: number;
  zones: Array<{
    zone: string;
    energy_wh: number;
    on_seconds: number;
  }>;
}

export interface ComparisonResponse {
  duration_s: number;
  runs: ComparisonRun[];
  difference_wh: number;
  salon_on_seconds: number;
  note: string;
}

export interface AuthMeResponse {
  authenticated: boolean;
  username: string;
  role: 'observer' | 'operator';
  operable_sites: string[];
}
