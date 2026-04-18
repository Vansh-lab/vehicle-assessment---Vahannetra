"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface VideoCaptureProps {
  onCapture: (file: File) => void;
}

export function VideoCapture({ onCapture }: VideoCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const [recording, setRecording] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let stream: MediaStream | null = null;
    const setup = async () => {
      if (!navigator?.mediaDevices?.getUserMedia) return;
      stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      if (videoRef.current) videoRef.current.srcObject = stream;
      setReady(true);
    };
    setup().catch(() => setReady(false));
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const startRecording = () => {
    const stream = videoRef.current?.srcObject;
    if (!(stream instanceof MediaStream)) return;
    chunksRef.current = [];
    const recorder = new MediaRecorder(stream, { mimeType: "video/webm" });
    recorderRef.current = recorder;
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "video/webm" });
      onCapture(new File([blob], `capture-${Date.now()}.webm`, { type: "video/webm" }));
    };
    recorder.start(250);
    setRecording(true);
  };

  const stopRecording = () => {
    recorderRef.current?.stop();
    setRecording(false);
  };

  return (
    <Card className="space-y-3">
      <p className="text-sm font-semibold text-slate-100">Video Capture</p>
      <video ref={videoRef} autoPlay muted playsInline className="w-full rounded-xl border border-white/15" />
      <div className="flex gap-2">
        <Button type="button" onClick={startRecording} disabled={!ready || recording}>
          Start
        </Button>
        <Button type="button" variant="secondary" onClick={stopRecording} disabled={!recording}>
          Stop
        </Button>
      </div>
    </Card>
  );
}
