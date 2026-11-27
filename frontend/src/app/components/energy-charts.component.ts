import { Component, computed, input } from '@angular/core';
import { GapItem, SeriesPoint, SiteKind, ZoneState } from '../models/pulso.models';
import { formatDecimal } from '../utils/format';

interface ChartLine {
  label: string;
  color: string;
  pointsAttr: string;
}

interface GapRect {
  x: number;
  width: number;
  label: string;
}

@Component({
  selector: 'app-energy-charts',
  standalone: true,
  template: `
    <div class="d-flex flex-column gap-3">
      <!-- Power Chart -->
      <section class="pulso-card p-3" aria-labelledby="chart-power-title">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
          <h2 id="chart-power-title" class="h6 fw-bold mb-0">
            Potencia (W) vs tiempo del ensayo (s)
          </h2>
          <div class="d-flex flex-wrap gap-2 small">
            @for (line of powerLines(); track line.label) {
              <span class="d-inline-flex align-items-center gap-1">
                <span
                  aria-hidden="true"
                  style="width:12px;height:3px;display:inline-block;"
                  [style.background-color]="line.color"
                ></span>
                {{ line.label }}
              </span>
            }
          </div>
        </div>

        <svg
          viewBox="0 0 760 190"
          class="w-100"
          style="height: auto; max-height: 210px;"
          role="img"
          [attr.aria-label]="'Gráfico de potencia en vatios respecto al tiempo'"
        >
          <rect x="54" y="12" width="690" height="142" fill="none" stroke="var(--chart-grid)" />
          <!-- Horizontal grid -->
          <line x1="54" y1="83" x2="744" y2="83" stroke="var(--chart-grid)" stroke-dasharray="4 4" />
          <line x1="54" y1="12" x2="744" y2="12" stroke="var(--chart-grid)" stroke-dasharray="4 4" />

          <!-- Gaps shaded -->
          @for (g of gapRects(); track g.x) {
            <rect
              [attr.x]="g.x"
              y="12"
              [attr.width]="g.width"
              height="142"
              fill="var(--warn-border)"
              fill-opacity="0.22"
            />
            <text
              [attr.x]="g.x + g.width / 2"
              y="28"
              text-anchor="middle"
              font-size="13"
              font-weight="700"
              fill="var(--warn-text)"
            >
              sin datos
            </text>
          }

          <!-- Axes -->
          <line x1="54" y1="154" x2="744" y2="154" stroke="var(--text)" stroke-width="1.5" />
          <line x1="54" y1="12" x2="54" y2="154" stroke="var(--text)" stroke-width="1.5" />

          <!-- Y labels -->
          <text x="48" y="18" text-anchor="end" font-size="13" fill="var(--text-muted)">
            {{ formatW(maxPower()) }}
          </text>
          <text x="48" y="87" text-anchor="end" font-size="13" fill="var(--text-muted)">
            {{ formatW(maxPower() / 2) }}
          </text>
          <text x="48" y="156" text-anchor="end" font-size="13" fill="var(--text-muted)">0 W</text>

          <!-- X labels -->
          <text x="54" y="176" font-size="13" fill="var(--text-muted)">0 s</text>
          <text x="744" y="176" text-anchor="end" font-size="13" fill="var(--text-muted)">
            {{ maxT() }} s
          </text>

          <!-- Series polylines -->
          @for (line of powerLines(); track line.label) {
            <polyline
              fill="none"
              [attr.stroke]="line.color"
              stroke-width="2.75"
              stroke-linejoin="round"
              [attr.points]="line.pointsAttr"
            />
          }
        </svg>
      </section>

      <!-- Energy Chart -->
      <section class="pulso-card p-3" aria-labelledby="chart-energy-title">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
          <h2 id="chart-energy-title" class="h6 fw-bold mb-0">
            Energía acumulada ({{ energyUnit() }}) · línea de umbral
          </h2>
          <span class="small fw-semibold" style="color: var(--danger-border);">
            --- Umbral: {{ formatThreshold() }}
          </span>
        </div>

        <svg
          viewBox="0 0 760 200"
          class="w-100"
          style="height: auto; max-height: 220px;"
          role="img"
          [attr.aria-label]="'Gráfico de energía acumulada con línea de umbral'"
        >
          <rect x="64" y="14" width="680" height="148" fill="none" stroke="var(--chart-grid)" />

          <!-- Gaps shaded -->
          @for (g of energyGapRects(); track g.x) {
            <rect
              [attr.x]="g.x"
              y="14"
              [attr.width]="g.width"
              height="148"
              fill="var(--warn-border)"
              fill-opacity="0.22"
            />
            <text
              [attr.x]="g.x + g.width / 2"
              y="30"
              text-anchor="middle"
              font-size="13"
              font-weight="700"
              fill="var(--warn-text)"
            >
              sin datos
            </text>
          }

          <!-- Threshold horizontal line -->
          <line
            x1="64"
            [attr.y1]="thresholdY()"
            x2="744"
            [attr.y2]="thresholdY()"
            stroke="var(--danger-border)"
            stroke-width="2"
            stroke-dasharray="6 4"
          />

          <!-- Axes -->
          <line x1="64" y1="162" x2="744" y2="162" stroke="var(--text)" stroke-width="1.5" />
          <line x1="64" y1="14" x2="64" y2="162" stroke="var(--text)" stroke-width="1.5" />

          <!-- Y labels -->
          <text x="58" y="20" text-anchor="end" font-size="13" fill="var(--text-muted)">
            {{ formatEnergyAxis(maxEnergy()) }}
          </text>
          <text x="58" y="90" text-anchor="end" font-size="13" fill="var(--text-muted)">
            {{ formatEnergyAxis(maxEnergy() / 2) }}
          </text>
          <text x="58" y="164" text-anchor="end" font-size="13" fill="var(--text-muted)">0</text>

          <!-- X labels -->
          <text x="64" y="184" font-size="13" fill="var(--text-muted)">0 s</text>
          <text x="744" y="184" text-anchor="end" font-size="13" fill="var(--text-muted)">
            {{ maxT() }} s
          </text>

          <!-- Energy lines -->
          @for (line of energyLines(); track line.label) {
            <polyline
              fill="none"
              [attr.stroke]="line.color"
              stroke-width="2.75"
              stroke-linejoin="round"
              [attr.points]="line.pointsAttr"
            />
          }
        </svg>
      </section>
    </div>
  `,
})
export class EnergyChartsComponent {
  readonly series = input.required<Record<string, SeriesPoint[]>>();
  readonly gaps = input.required<GapItem[]>();
  readonly zones = input.required<ZoneState[]>();
  readonly thresholdWh = input.required<number>();
  readonly siteKind = input.required<SiteKind>();

  readonly energyUnit = computed(() => (this.siteKind() === 'venue' ? 'kWh' : 'Wh'));

  readonly maxT = computed(() => {
    let max = 1;
    for (const pts of Object.values(this.series())) {
      for (const p of pts) {
        if (p.t_s > max) max = p.t_s;
      }
    }
    for (const g of this.gaps()) {
      if (g.to_t_s > max) max = g.to_t_s;
    }
    return max;
  });

  readonly maxPower = computed(() => {
    let max = 2;
    for (const pts of Object.values(this.series())) {
      for (const p of pts) {
        if (p.power_w > max) max = p.power_w;
      }
    }
    return max * 1.15;
  });

  readonly maxEnergy = computed(() => {
    let max = this.thresholdWh() > 0 ? this.thresholdWh() : 0.02;
    for (const pts of Object.values(this.series())) {
      for (const p of pts) {
        if (p.energy_wh > max) max = p.energy_wh;
      }
    }
    return max * 1.12;
  });

  readonly thresholdY = computed(() => {
    const ratio = Math.min(1, Math.max(0, this.thresholdWh() / this.maxEnergy()));
    return 162 - ratio * 148;
  });

  readonly powerLines = computed<ChartLine[]>(() => {
    return this.buildLines('power', 54, 690, 12, 142, this.maxPower());
  });

  readonly energyLines = computed<ChartLine[]>(() => {
    return this.buildLines('energy', 64, 680, 14, 148, this.maxEnergy());
  });

  readonly gapRects = computed<GapRect[]>(() => {
    return this.buildGaps(54, 690);
  });

  readonly energyGapRects = computed<GapRect[]>(() => {
    return this.buildGaps(64, 680);
  });

  private buildGaps(left: number, width: number): GapRect[] {
    const tMax = this.maxT();
    return this.gaps().map((g) => {
      const x1 = left + (g.from_t_s / tMax) * width;
      const x2 = left + (g.to_t_s / tMax) * width;
      return {
        x: x1,
        width: Math.max(24, x2 - x1),
        label: g.label,
      };
    });
  }

  private buildLines(
    mode: 'power' | 'energy',
    left: number,
    width: number,
    top: number,
    height: number,
    yMax: number
  ): ChartLine[] {
    const tMax = this.maxT();
    const s = this.series();
    const result: ChartLine[] = [];
    const zoneColors = ['var(--chart-zone-1)', 'var(--chart-zone-2)'];

    if (this.siteKind() === 'venue') {
      this.zones().forEach((z, idx) => {
        const pts = s[z.slug];
        if (pts && pts.length > 0) {
          result.push({
            label: z.name,
            color: zoneColors[idx % zoneColors.length],
            pointsAttr: this.toPoints(pts, mode, left, width, top, height, tMax, yMax),
          });
        }
      });
    }

    const totalPts = s['total'] ?? Object.values(s)[0] ?? [];
    if (totalPts.length > 0) {
      result.push({
        label: 'Total',
        color: 'var(--chart-total)',
        pointsAttr: this.toPoints(totalPts, mode, left, width, top, height, tMax, yMax),
      });
    }

    return result;
  }

  private toPoints(
    pts: SeriesPoint[],
    mode: 'power' | 'energy',
    left: number,
    width: number,
    top: number,
    height: number,
    tMax: number,
    yMax: number
  ): string {
    return pts
      .map((p) => {
        const x = left + (p.t_s / tMax) * width;
        const val = mode === 'power' ? p.power_w : p.energy_wh;
        const y = top + height - (val / yMax) * height;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }

  formatW(val: number): string {
    return `${formatDecimal(val, 1)} W`;
  }

  formatEnergyAxis(wh: number): string {
    if (this.siteKind() === 'venue') {
      return formatDecimal(wh / 1000, 2);
    }
    return formatDecimal(wh, 3);
  }

  formatThreshold(): string {
    if (this.siteKind() === 'venue') {
      return `${formatDecimal(this.thresholdWh() / 1000, 3)} kWh`;
    }
    return `${formatDecimal(this.thresholdWh(), 4)} Wh`;
  }
}
