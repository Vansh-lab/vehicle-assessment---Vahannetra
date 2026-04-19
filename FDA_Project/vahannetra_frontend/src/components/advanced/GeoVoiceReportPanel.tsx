"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { jsPDF } from "jspdf";

import type { DamageFinding } from "@/types/domain";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { env } from "@/lib/env";

type Position = { lat: number; lng: number } | null;
const WAVE_BAR_DELAY_MS = 70;
const WAVE_BAR_BASE_HEIGHT_PX = 10;
const WAVE_BAR_HEIGHT_STEP_PX = 5;
const WAVE_BAR_VARIANTS = 3;

type SpeechRecognitionCtor = new () => {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: { results: { 0: { 0: { transcript: string } } } }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

interface GeoVoiceReportPanelProps {
  findings: DamageFinding[];
  triageCategory: string;
  healthScore: number;
}

export function GeoVoiceReportPanel({ findings, triageCategory, healthScore }: GeoVoiceReportPanelProps) {
  const [position, setPosition] = useState<Position>(null);
  const [locationLabel, setLocationLabel] = useState("Location unavailable");
  const [loadingLocation, setLoadingLocation] = useState(false);
  const [voiceNotes, setVoiceNotes] = useState("");
  const [voiceError, setVoiceError] = useState("");
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState<string>("");
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const recognitionRef = useRef<{
    stop: () => void;
  } | null>(null);

  const summaryText = useMemo(() => {
    const high = findings.filter((item) => item.severity === "high").length;
    return `Inspection summary. Health score ${healthScore}. Triage category ${triageCategory}. Total findings ${findings.length}. High severity findings ${high}.`;
  }, [findings, healthScore, triageCategory]);

  useEffect(() => {
    if (!("speechSynthesis" in window)) return;
    const updateVoices = () => {
      const list = window.speechSynthesis.getVoices();
      setVoices(list);
      if (!selectedVoice && list[0]) {
        setSelectedVoice(list[0].name);
      }
    };
    updateVoices();
    window.speechSynthesis.onvoiceschanged = updateVoices;
    return () => {
      window.speechSynthesis.onvoiceschanged = null;
    };
  }, [selectedVoice]);

  const mapUrl = position
    ? `https://www.openstreetmap.org/export/embed.html?layer=mapnik&marker=${position.lat}%2C${position.lng}`
    : "https://www.openstreetmap.org/export/embed.html?layer=mapnik";

  const fetchCurrentLocation = async () => {
    if (!navigator.geolocation) {
      setLocationLabel("Geolocation is not supported by this browser.");
      return;
    }
    setLoadingLocation(true);
    navigator.geolocation.getCurrentPosition(
      async (geo) => {
        const lat = Number(geo.coords.latitude.toFixed(6));
        const lng = Number(geo.coords.longitude.toFixed(6));
        setPosition({ lat, lng });
        try {
          const nominatimUrl =
            `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}` +
            `&email=${encodeURIComponent(env.NOMINATIM_CONTACT_EMAIL)}`;
          const response = await fetch(nominatimUrl, {
            headers: {
              "Accept-Language": "en-IN,en;q=0.9",
              "X-VahanNetra-Client": "VahanNetra",
            },
          });
          if (!response.ok) throw new Error("reverse geocode failed");
          const payload = (await response.json()) as { display_name?: string; address?: { city?: string; town?: string; state?: string } };
          const city = payload.address?.city || payload.address?.town || "";
          setLocationLabel(city ? `${city} • ${payload.display_name || `${lat}, ${lng}`}` : (payload.display_name || `${lat}, ${lng}`));
        } catch {
          setLocationLabel(`${lat}, ${lng}`);
        } finally {
          setLoadingLocation(false);
        }
      },
      () => {
        setLocationLabel("Location permission denied.");
        setLoadingLocation(false);
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 15000 },
    );
  };

  const exportPdf = () => {
    const pdf = new jsPDF({ unit: "mm", format: "a4" });
    pdf.setFontSize(16);
    pdf.text("VahanNetra - Inspection Summary", 14, 14);
    pdf.setFontSize(10);
    pdf.text(`Health Score: ${healthScore}`, 14, 22);
    pdf.text(`Triage Category: ${triageCategory}`, 14, 28);
    pdf.text(`Findings: ${findings.length}`, 14, 34);
    pdf.text(`Location: ${locationLabel}`, 14, 40, { maxWidth: 180 });

    let y = 50;
    pdf.setFontSize(11);
    pdf.text("Findings Table", 14, y);
    y += 6;
    findings.slice(0, 10).forEach((item, index) => {
      pdf.setFontSize(9);
      pdf.text(
        `${index + 1}. ${item.type} | ${item.severity} | ₹${item.estimateMin.toLocaleString()} - ₹${item.estimateMax.toLocaleString()}`,
        14,
        y,
      );
      y += 5;
      if (y > 280) {
        pdf.addPage();
        y = 20;
      }
    });

    pdf.setFontSize(8);
    pdf.text("Generated by VahanNetra web client", 14, 290);
    pdf.save(`inspection-${Date.now()}.pdf`);
  };

  const speakSummary = () => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(summaryText);
    const voice = voices.find((v) => v.name === selectedVoice);
    if (voice) utterance.voice = voice;
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  };

  const stopVoiceCapture = () => {
    recognitionRef.current?.stop();
    setIsListening(false);
  };

  const captureVoiceNotes = () => {
    const SpeechRecognition = (
      window as Window & {
        webkitSpeechRecognition?: SpeechRecognitionCtor;
        SpeechRecognition?: SpeechRecognitionCtor;
      }
    ).webkitSpeechRecognition
      ?? (
        window as Window & {
          webkitSpeechRecognition?: SpeechRecognitionCtor;
          SpeechRecognition?: SpeechRecognitionCtor;
        }
      ).SpeechRecognition;
    if (!SpeechRecognition) {
      setVoiceError("Speech recognition is not supported in this browser.");
      return;
    }
    setVoiceError("");
    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognitionRef.current = recognition;
    setIsListening(true);
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript ?? "";
      setVoiceNotes(transcript);
      setIsListening(false);
    };
    recognition.onerror = () => {
      setVoiceError("Unable to capture voice notes.");
      setIsListening(false);
    };
    recognition.onend = () => setIsListening(false);
    recognition.start();
  };

  return (
    <Card className="space-y-3">
      <p className="text-sm font-semibold text-slate-100">Geo + Voice + PDF Assistant</p>

      <div className="flex flex-wrap gap-2">
        <Button type="button" onClick={() => void fetchCurrentLocation()}>
          {loadingLocation ? "Locating..." : "Use GPS location"}
        </Button>
        <Button type="button" variant="secondary" onClick={exportPdf}>
          Export jsPDF report
        </Button>
        <Button type="button" variant="secondary" onClick={speakSummary}>
          Speak summary
        </Button>
        <Button type="button" variant="secondary" onClick={stopSpeaking} disabled={!isSpeaking}>
          Stop voice
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={isListening ? stopVoiceCapture : captureVoiceNotes}
        >
          {isListening ? "Stop capture" : "Capture voice notes"}
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <label className="text-xs text-slate-300" htmlFor="voice-select">Voice:</label>
        <select
          id="voice-select"
          value={selectedVoice}
          onChange={(event) => setSelectedVoice(event.target.value)}
          className="rounded border border-white/20 bg-slate-900 px-2 py-1 text-xs text-slate-200"
        >
          {voices.map((voice) => (
            <option key={voice.name} value={voice.name}>{voice.name}</option>
          ))}
        </select>
      </div>

      {isSpeaking || isListening ? (
        <div className="flex items-end gap-1">
          {[1, 2, 3, 4, 5].map((bar) => (
            <span
              key={bar}
              className="w-1 animate-pulse rounded bg-cyan-300"
              style={{
                animationDelay: `${bar * WAVE_BAR_DELAY_MS}ms`,
                height: `${WAVE_BAR_BASE_HEIGHT_PX + ((bar % WAVE_BAR_VARIANTS) * WAVE_BAR_HEIGHT_STEP_PX)}px`,
              }}
            />
          ))}
          <span className="text-xs text-cyan-200">
            {isListening ? "Listening..." : "Speaking..."}
          </span>
        </div>
      ) : null}

      <p className="text-xs text-slate-300">{locationLabel}</p>
      <iframe
        title="Inspection location map"
        className="h-56 w-full rounded-xl border border-white/10"
        loading="lazy"
        src={mapUrl}
      />

      <div className="space-y-1">
        <p className="text-xs font-medium text-slate-200">Voice notes</p>
        <p className="min-h-8 rounded border border-white/10 px-2 py-1 text-xs text-slate-300">
          {voiceNotes || "No voice note captured yet."}
        </p>
        {voiceError ? <p className="text-xs text-rose-200">{voiceError}</p> : null}
      </div>
    </Card>
  );
}
