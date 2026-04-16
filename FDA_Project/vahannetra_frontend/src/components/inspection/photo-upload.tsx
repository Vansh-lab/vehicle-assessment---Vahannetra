"use client";

import { useRef, useState } from "react";
import { Camera, ImagePlus, RotateCcw, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface PhotoUploadProps {
  file: File | null;
  onFileChange: (file: File | null) => void;
}

export function PhotoUpload({ file, onFileChange }: PhotoUploadProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const galleryInputRef = useRef<HTMLInputElement>(null);

  const validateImage = (pickedFile: File) => {
    const nextWarnings: string[] = [];
    if (pickedFile.size < 40_000) nextWarnings.push("Blurry image warning: File size is low, so image may be blurry. Please retake for reliable AI output.");
    if (pickedFile.size < 120_000) nextWarnings.push("Low-light warning: Small file size may indicate poor lighting/compression; capture again in brighter light.");
    setWarnings(nextWarnings);
  };

  const handleFile = (pickedFile: File | null) => {
    if (!pickedFile) return;
    onFileChange(pickedFile);
    setPreviewUrl(URL.createObjectURL(pickedFile));
    validateImage(pickedFile);
  };

  return (
    <Card>
      <p className="text-sm font-semibold text-slate-100">Upload inspection image</p>
      <p className="mt-1 text-xs text-slate-400">Supports mobile camera capture, gallery and drag-drop upload.</p>

      <div
        className="mt-4 rounded-xl border border-dashed border-white/15 px-4 py-8 text-center text-sm text-slate-500"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          const dropped = event.dataTransfer.files?.[0];
          if (dropped) handleFile(dropped);
        }}
      >
        Drop image here or use quick actions below.
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <Button variant="secondary" onClick={() => cameraInputRef.current?.click()}>
          <Camera size={16} className="mr-2" /> Camera
        </Button>
        <Button variant="secondary" onClick={() => galleryInputRef.current?.click()}>
          <ImagePlus size={16} className="mr-2" /> Gallery
        </Button>
      </div>

      <input ref={cameraInputRef} className="hidden" type="file" accept="image/*" capture="environment" onChange={(event) => handleFile(event.target.files?.[0] ?? null)} />
      <input ref={galleryInputRef} className="hidden" type="file" accept="image/*" onChange={(event) => handleFile(event.target.files?.[0] ?? null)} />

      {previewUrl ? (
        <div className="mt-4 overflow-hidden rounded-xl border border-white/10">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={previewUrl} alt="inspection preview" className="h-56 w-full object-cover" />
        </div>
      ) : null}

      {warnings.length ? (
        <div className="mt-3 space-y-2">
          {warnings.map((warning) => (
            <div key={warning} className="flex items-start gap-2 rounded-xl border border-amber-300/30 bg-amber-300/10 p-3 text-xs text-amber-100">
              <TriangleAlert size={16} className="mt-0.5" />
              <p>{warning}</p>
            </div>
          ))}
        </div>
      ) : null}

      {file ? (
        <Button variant="ghost" className="mt-3" onClick={() => handleFile(file)}>
          <RotateCcw size={16} className="mr-2" /> Retake / Re-select
        </Button>
      ) : null}
    </Card>
  );
}
