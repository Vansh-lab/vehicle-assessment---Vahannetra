"use client";

import { useMemo, useState } from "react";
import { jsPDF } from "jspdf";

import type { DamageFinding } from "@/types/domain";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

type Position = { lat: number; lng: number } | null;
type SpeechRecognitionCtor = new () => {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: { results: { 0: { 0: { transcript: string } } } }) => void) | null;
  onerror: (() => void) | null;
  start: () => void;
};

interface GeoVoiceReportPanelProps {
  findings: DamageFinding[];
  triageCategory: string;
  healthScore: number;
}

export function GeoVoiceReportPanel({
  findings,
  triageCategory,
  healthScore,
}: GeoVoiceReportPanelProps) {
  const [position, setPosition] = useState<Position>(null);
  const [locationLabel, setLocationLabel] = useState("Location unavailable");
  const [loadingLocation, setLoadingLocation] = useState(false);
  const [voiceNotes, setVoiceNotes] = useState("");
  const [voiceError, setVoiceError] = useState("");

  const summaryText = useMemo(() => {
    const high = findings.filter((item) => item.severity === "high").length;
    return `Inspection summary. Health score ${healthScore}. Triage category ${triageCategory}. Total findings ${findings.length}. High severity findings ${high}.`;
  }, [findings, healthScore, triageCategory]);

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
            `&email=support@vahannetra.local`;
          const response = await fetch(
            nominatimUrl,
            {
              headers: {
                "Accept-Language": "en-IN,en;q=0.9",
                "X-Client": "VahanNetra",
              },
            }
          );
          if (!response.ok) throw new Error("reverse geocode failed");
          const payload = (await response.json()) as { display_name?: string };
          setLocationLabel(payload.display_name || `${lat}, ${lng}`);
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
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 15000 }
    );
  };

  const exportPdf = () => {
    const pdf = new jsPDF();
    pdf.setFontSize(14);
    pdf.text("VahanNetra - Inspection Summary", 14, 18);
    pdf.setFontSize(11);
    pdf.text(`Health Score: ${healthScore}`, 14, 30);
    pdf.text(`Triage Category: ${triageCategory}`, 14, 38);
    pdf.text(`Findings: ${findings.length}`, 14, 46);
    pdf.text(`Location: ${locationLabel}`, 14, 54, { maxWidth: 180 });
    let y = 68;
    findings.slice(0, 8).forEach((item, index) => {
      pdf.text(
        `${index + 1}. ${item.type} | ${item.severity} | ₹${item.estimateMin.toLocaleString()} - ₹${item.estimateMax.toLocaleString()}`,
        14,
        y
      );
      y += 8;
    });
    pdf.save(`inspection-${Date.now()}.pdf`);
  };

  const speakSummary = () => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(summaryText);
    utterance.rate = 1;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
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
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript ?? "";
      setVoiceNotes(transcript);
    };
    recognition.onerror = () => setVoiceError("Unable to capture voice notes.");
    recognition.start();
  };

  return (
    <Card className="space-y-3">
      <p className="text-sm font-semibold text-slate-100">
        Geo + Voice + PDF Assistant
      </p>

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
        <Button type="button" variant="secondary" onClick={captureVoiceNotes}>
          Capture voice notes
        </Button>
      </div>

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
