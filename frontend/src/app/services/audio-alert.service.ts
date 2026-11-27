import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class AudioAlertService {
  readonly soundEnabled = signal(false);
  readonly lastBeepAt = signal<string | null>(null);
  private audioCtx: AudioContext | null = null;

  enableSound(): void {
    if (typeof window === 'undefined') {
      return;
    }
    const AudioCtx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (AudioCtx && !this.audioCtx) {
      this.audioCtx = new AudioCtx();
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      void this.audioCtx.resume();
    }
    this.soundEnabled.set(true);
  }

  disableSound(): void {
    this.soundEnabled.set(false);
  }

  hasPlayedInSession(alertId: string): boolean {
    if (typeof sessionStorage === 'undefined') {
      return false;
    }
    return sessionStorage.getItem(`pulso_alert_seen_${alertId}`) === '1';
  }

  markSeenInSession(alertId: string): void {
    if (typeof sessionStorage === 'undefined') {
      return;
    }
    sessionStorage.setItem(`pulso_alert_seen_${alertId}`, '1');
  }

  triggerAlertBeepIfNew(alertId: string): boolean {
    if (!alertId || this.hasPlayedInSession(alertId)) {
      return false;
    }
    if (!this.soundEnabled()) {
      return false;
    }
    this.markSeenInSession(alertId);
    this.playBeep08s();
    return true;
  }

  private playBeep08s(): void {
    if (!this.audioCtx) {
      this.enableSound();
    }
    if (!this.audioCtx) {
      return;
    }
    const ctx = this.audioCtx;
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, now);

    gain.gain.setValueAtTime(0.001, now);
    gain.gain.exponentialRampToValueAtTime(0.22, now + 0.04);
    gain.gain.setValueAtTime(0.22, now + 0.72);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.8);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.8);
    this.lastBeepAt.set(new Date().toLocaleTimeString('es-CL'));
  }
}
