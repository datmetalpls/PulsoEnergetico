import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class SpeechReportService {
  readonly speaking = signal(false);
  readonly supported = signal(
    typeof window !== 'undefined' && 'speechSynthesis' in window
  );
  readonly selectedVoiceName = signal<string | null>(null);

  speak(text: string): void {
    if (!this.supported() || !text.trim()) {
      return;
    }
    const synth = window.speechSynthesis;
    synth.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    const voices = synth.getVoices();
    const preferred =
      voices.find((v) => v.lang.toLowerCase() === 'es-cl') ||
      voices.find((v) => v.lang.toLowerCase() === 'es-ec') ||
      voices.find((v) => v.lang.toLowerCase().startsWith('es'));

    if (preferred) {
      utterance.voice = preferred;
      utterance.lang = preferred.lang;
      this.selectedVoiceName.set(`${preferred.name} (${preferred.lang})`);
    } else {
      utterance.lang = 'es-CL';
      this.selectedVoiceName.set('Voz predeterminada (es-CL)');
    }

    utterance.rate = 1.0;
    utterance.onstart = () => this.speaking.set(true);
    utterance.onend = () => this.speaking.set(false);
    utterance.onerror = () => this.speaking.set(false);

    synth.speak(utterance);
  }

  stop(): void {
    if (!this.supported()) {
      return;
    }
    window.speechSynthesis.cancel();
    this.speaking.set(false);
  }
}
