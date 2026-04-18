"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface VideoCaptureProps {
  onVideoReady?: (blob: Blob) => void;
  onCapture?: (file: File) => void;
}

type PermissionState = "idle" | "requesting" | "granted" | "denied";

function VideoCapture({ onVideoReady, onCapture }: VideoCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const [permission, setPermission] = useState<PermissionState>("idle");
  const [recording, setRecording] = useState(false);
  const [stopped, setStopped] = useState(false);
  const [videoBlob, setVideoBlob] = useState<Blob | null>(null);
  const [duration, setDuration] = useState(0);
  const [facingMode, setFacingMode] = useState<"environment" | "user">("environment");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [captureError, setCaptureError] = useState("");
  const MAX_DURATION = 30;

  const clearPreview = useCallback(() => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
  }, [previewUrl]);

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const requestCameraForMode = useCallback(async (mode: "environment" | "user") => {
    setPermission("requesting");
    stopStream();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: mode, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setPermission("granted");
    } catch {
      setPermission("denied");
    }
  }, [stopStream]);

  const startCamera = useCallback(async () => {
    await requestCameraForMode(facingMode);
  }, [facingMode, requestCameraForMode]);

  const switchCamera = useCallback(async () => {
    const nextMode = facingMode === "environment" ? "user" : "environment";
    setFacingMode(nextMode);
    await requestCameraForMode(nextMode);
  }, [facingMode, requestCameraForMode]);

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  }, []);

  const startRecording = useCallback(() => {
    if (!(streamRef.current instanceof MediaStream)) return;
    chunksRef.current = [];
    const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
      ? "video/webm;codecs=vp9"
      : MediaRecorder.isTypeSupported("video/webm;codecs=vp8")
        ? "video/webm;codecs=vp8"
        : MediaRecorder.isTypeSupported("video/webm")
          ? "video/webm"
          : "";
    if (!mimeType) {
      setCaptureError("Recording is not supported in this browser. Please upload a video file.");
      return;
    }
    const recorder = new MediaRecorder(streamRef.current, { mimeType });
    mediaRecorderRef.current = recorder;
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: mimeType });
      setVideoBlob(blob);
      clearPreview();
      setPreviewUrl(URL.createObjectURL(blob));
      setStopped(true);
    };
    recorder.start(100);
    setDuration(0);
    setCaptureError("");
    setStopped(false);
    setRecording(true);
  }, [clearPreview]);

  useEffect(() => {
    if (!recording) return undefined;
    const interval = setInterval(() => {
      setDuration((prev) => {
        if (prev >= MAX_DURATION - 1) {
          stopRecording();
          return MAX_DURATION;
        }
        return prev + 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [recording, stopRecording]);

  const useRecordedVideo = useCallback(() => {
    if (!videoBlob) return;
    onVideoReady?.(videoBlob);
    if (onCapture) {
      const file = new File([videoBlob], `capture-${Date.now()}.webm`, {
        type: videoBlob.type || "video/webm",
      });
      onCapture(file);
    }
  }, [onCapture, onVideoReady, videoBlob]);

  const reRecord = useCallback(() => {
    setVideoBlob(null);
    setStopped(false);
    setDuration(0);
    clearPreview();
  }, [clearPreview]);

  useEffect(
    () => () => {
      stopStream();
      clearPreview();
    },
    [clearPreview, stopStream],
  );

  const countdown = useMemo(() => MAX_DURATION - duration, [duration]);

  return (
    <Card className="space-y-3">
      <p className="text-sm font-semibold text-slate-100">Video Capture (max 30s)</p>

      {permission === "idle" || permission === "requesting" ? (
        <Button type="button" onClick={() => void startCamera()} disabled={permission === "requesting"}>
          {permission === "requesting" ? "Requesting camera..." : "Enable camera"}
        </Button>
      ) : null}

      {permission === "denied" ? (
        <div className="space-y-2 text-xs text-amber-200">
          <p>Camera access denied. You can still upload a video manually.</p>
          <input
            type="file"
            accept="video/mp4,video/webm,video/quicktime"
            onChange={(event) => {
              const picked = event.target.files?.[0];
              if (!picked) return;
              onVideoReady?.(picked);
              onCapture?.(picked);
            }}
          />
        </div>
      ) : null}

      {captureError ? <p className="text-xs text-rose-200">{captureError}</p> : null}

      {permission === "granted" && !stopped ? (
        <>
          <video ref={videoRef} autoPlay muted playsInline className="w-full rounded-xl border border-white/15" />
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={startRecording} disabled={recording}>
              Start recording
            </Button>
            <Button type="button" variant="secondary" onClick={stopRecording} disabled={!recording}>
              Stop
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => void switchCamera()}
              disabled={recording}
            >
              Switch camera
            </Button>
          </div>
          {recording ? <p className="text-xs text-cyan-200">Recording... {duration}s / {MAX_DURATION}s (remaining {countdown}s)</p> : null}
        </>
      ) : null}

      {stopped && previewUrl ? (
        <div className="space-y-2">
          <video src={previewUrl} controls className="w-full rounded-xl border border-white/15" />
          <div className="flex gap-2">
            <Button type="button" onClick={useRecordedVideo}>
              Use this video
            </Button>
            <Button type="button" variant="secondary" onClick={reRecord}>
              Record again
            </Button>
          </div>
        </div>
      ) : null}
    </Card>
  );
}


export default VideoCapture;
