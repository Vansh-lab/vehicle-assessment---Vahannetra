"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, ImagePlus, RotateCcw, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface PhotoUploadProps {
  file: File | null;
  onFileChange: (file: File | null) => void;
}

async function readImageMetrics(file: File): Promise<{ brightness: number; edgeVariance: number }> {
  const imageUrl = URL.createObjectURL(file);
  try {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = imageUrl;
    });

    const width = Math.min(640, image.naturalWidth || image.width || 640);
    const height = Math.max(1, Math.round((width / (image.naturalWidth || width)) * (image.naturalHeight || width)));

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) return { brightness: 0, edgeVariance: 0 };

    context.drawImage(image, 0, 0, width, height);
    const { data } = context.getImageData(0, 0, width, height);

    const gray = new Float32Array(width * height);
    let sum = 0;
    for (let i = 0; i < gray.length; i += 1) {
      const p = i * 4;
      const value = 0.299 * data[p] + 0.587 * data[p + 1] + 0.114 * data[p + 2];
      gray[i] = value;
      sum += value;
    }

    const brightness = sum / gray.length;
    let laplacianSum = 0;
    let laplacianSumSq = 0;
    let count = 0;

    for (let y = 1; y < height - 1; y += 1) {
      for (let x = 1; x < width - 1; x += 1) {
        const idx = y * width + x;
        const laplacian =
          4 * gray[idx] - gray[idx - 1] - gray[idx + 1] - gray[idx - width] - gray[idx + width];
        laplacianSum += laplacian;
        laplacianSumSq += laplacian * laplacian;
        count += 1;
      }
    }

    const mean = count ? laplacianSum / count : 0;
    const edgeVariance = count ? laplacianSumSq / count - mean * mean : 0;

    return { brightness, edgeVariance };
  } finally {
    URL.revokeObjectURL(imageUrl);
  }
}

export function PhotoUpload({ file, onFileChange }: PhotoUploadProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const galleryInputRef = useRef<HTMLInputElement>(null);
  const previewObjectUrlRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      if (previewObjectUrlRef.current) {
        URL.revokeObjectURL(previewObjectUrlRef.current);
      }
    };
  }, []);

  const isSupportedImageFile = (candidate: File): boolean => candidate.type.startsWith("image/");

  const validateImage = async (pickedFile: File) => {
    const nextWarnings: string[] = [];

    if (pickedFile.size < 80_000) {
      nextWarnings.push("Image file looks heavily compressed; high-quality capture is recommended.");
    }

    try {
      const metrics = await readImageMetrics(pickedFile);
      if (metrics.brightness < 60) {
        nextWarnings.push("Low-light warning: image brightness is low. Capture in brighter light.");
      }
      if (metrics.brightness > 220) {
        nextWarnings.push("Overexposure warning: highlights are too strong. Reduce glare and retake.");
      }
      if (metrics.edgeVariance < 45) {
        nextWarnings.push("Blur warning: low edge sharpness detected. Hold camera steady and retake.");
      }
    } catch {
      nextWarnings.push("Could not compute image quality metrics. Ensure image is clear and well-lit.");
    }

    setWarnings(nextWarnings);
  };

  const handleFile = async (pickedFile: File | null) => {
    if (!pickedFile || !isSupportedImageFile(pickedFile)) {
      onFileChange(null);
      if (previewObjectUrlRef.current) {
        URL.revokeObjectURL(previewObjectUrlRef.current);
        previewObjectUrlRef.current = null;
      }
      setPreviewUrl(null);
      setWarnings(["Unsupported file type. Please upload a valid image file."]);
      return;
    }

    onFileChange(pickedFile);
    const nextPreviewUrl = URL.createObjectURL(pickedFile);
    if (previewObjectUrlRef.current) {
      URL.revokeObjectURL(previewObjectUrlRef.current);
    }
    previewObjectUrlRef.current = nextPreviewUrl;
    setPreviewUrl(nextPreviewUrl);
    await validateImage(pickedFile);
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
          if (dropped) {
            void handleFile(dropped);
          }
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

      <input
        ref={cameraInputRef}
        className="hidden"
        type="file"
        accept="image/*"
        capture="environment"
        onChange={(event) => {
          void handleFile(event.target.files?.[0] ?? null);
        }}
      />
      <input
        ref={galleryInputRef}
        className="hidden"
        type="file"
        accept="image/*"
        onChange={(event) => {
          void handleFile(event.target.files?.[0] ?? null);
        }}
      />

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
        <Button variant="ghost" className="mt-3" onClick={() => void handleFile(file)}>
          <RotateCcw size={16} className="mr-2" /> Retake / Re-select
        </Button>
      ) : null}
    </Card>
  );
}
