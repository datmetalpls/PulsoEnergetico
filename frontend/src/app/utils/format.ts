import { SiteKind } from '../models/pulso.models';

const formatters = new Map<number, Intl.NumberFormat>();

function getFormatter(decimals: number): Intl.NumberFormat {
  let fmt = formatters.get(decimals);
  if (!fmt) {
    fmt = new Intl.NumberFormat('es-CL', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
    formatters.set(decimals, fmt);
  }
  return fmt;
}

export function formatDecimal(value: number, decimals: number): string {
  const safe = Number.isFinite(value) ? value : 0;
  return getFormatter(decimals).format(safe);
}

export function formatPower(powerW: number): string {
  return `${formatDecimal(powerW, 2)} W`;
}

export function formatEnergy(energyWh: number, kind: SiteKind): string {
  if (kind === 'venue') {
    return `${formatDecimal(energyWh / 1000, 3)} kWh`;
  }
  return `${formatDecimal(energyWh, 4)} Wh`;
}

export function formatCurrent(currentA: number): string {
  return `${formatDecimal(currentA, 2)} A`;
}

export function formatVoltage(voltageV: number): string {
  return `${formatDecimal(voltageV, 2)} V`;
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds)) {
    return 'Consumo detenido';
  }
  const total = Math.max(0, Math.round(seconds));
  if (total < 60) {
    return `${total} s`;
  }
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hours > 0) {
    return `${hours} h ${minutes} min`;
  }
  return secs > 0 ? `${minutes} min ${secs} s` : `${minutes} min`;
}

export function sourceLabel(source: string): string {
  switch (source) {
    case 'simulator':
      return 'Simulador local';
    case 'wokwi_import':
      return 'Lecturas importadas de Wokwi';
    case 'device':
      return 'Dispositivo físico';
    default:
      return source;
  }
}
