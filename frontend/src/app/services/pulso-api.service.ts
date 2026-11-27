import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  AuthMeResponse,
  ComparisonResponse,
  LocalityWithSites,
  ReportResponse,
  StateResponse,
} from '../models/pulso.models';

@Injectable({ providedIn: 'root' })
export class PulsoApiService {
  private readonly http = inject(HttpClient);

  getCsrf(): Observable<unknown> {
    return this.http.get('/api/auth/csrf');
  }

  getMe(): Observable<AuthMeResponse> {
    return this.http.get<AuthMeResponse>('/api/auth/me');
  }

  login(username: string, password: string): Observable<AuthMeResponse> {
    return this.http.post<AuthMeResponse>('/api/auth/login', {
      username,
      password,
    });
  }

  logout(): Observable<unknown> {
    return this.http.post('/api/auth/logout', {});
  }

  getLocalities(): Observable<LocalityWithSites[]> {
    return this.http.get<LocalityWithSites[]>('/api/localities');
  }

  getState(siteSlug: string): Observable<StateResponse> {
    return this.http.get<StateResponse>(`/api/sites/${siteSlug}/state`);
  }

  updateSiteBudget(siteSlug: string, budgetKwhDay: number): Observable<StateResponse> {
    return this.http.patch<StateResponse>(`/api/sites/${siteSlug}`, {
      budget_kwh_day: budgetKwhDay,
    });
  }

  startSession(siteSlug: string, thresholdWh?: number): Observable<StateResponse> {
    const body = thresholdWh !== undefined ? { threshold_wh: thresholdWh } : {};
    return this.http.post<StateResponse>(`/api/sites/${siteSlug}/sessions`, body);
  }

  play(sessionId: string): Observable<StateResponse> {
    return this.http.post<StateResponse>(`/api/sessions/${sessionId}/play`, {});
  }

  pause(sessionId: string): Observable<StateResponse> {
    return this.http.post<StateResponse>(`/api/sessions/${sessionId}/pause`, {});
  }

  nextBand(sessionId: string): Observable<StateResponse> {
    return this.http.post<StateResponse>(`/api/sessions/${sessionId}/next-band`, {});
  }

  setSpeed(sessionId: string, speed: number): Observable<StateResponse> {
    return this.http.post<StateResponse>(`/api/sessions/${sessionId}/speed`, { speed });
  }

  updateZone(
    sessionId: string,
    zoneSlug: string,
    payload: { on?: boolean; current_a?: number; intensity_pct?: number }
  ): Observable<StateResponse> {
    return this.http.post<StateResponse>(
      `/api/sessions/${sessionId}/zones/${zoneSlug}`,
      payload
    );
  }

  setConnection(sessionId: string, connected: boolean): Observable<StateResponse> {
    return this.http.post<StateResponse>(`/api/sessions/${sessionId}/connection`, {
      connected,
    });
  }

  importReadings(sessionId: string, payload: unknown): Observable<StateResponse> {
    return this.http.post<StateResponse>(`/api/sessions/${sessionId}/readings`, payload);
  }

  ackAlert(sessionId: string, alertId: string): Observable<StateResponse> {
    return this.http.post<StateResponse>(
      `/api/sessions/${sessionId}/alerts/${alertId}/ack`,
      {}
    );
  }

  getReport(sessionId: string): Observable<ReportResponse> {
    return this.http.get<ReportResponse>(`/api/sessions/${sessionId}/report`);
  }

  getComparison(siteSlug: string): Observable<ComparisonResponse> {
    return this.http.get<ComparisonResponse>(
      `/api/sites/${siteSlug}/comparison?duration_s=21600&meeting_end_s=10800`
    );
  }
}
