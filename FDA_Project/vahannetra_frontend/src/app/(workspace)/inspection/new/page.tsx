"use client";

import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { CaptureAngle, VehicleType } from "@/types/domain";
import { useInspectionStore } from "@/store/inspection-store";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { InspectionStepper } from "@/components/inspection/inspection-stepper";
import { PhotoUpload } from "@/components/inspection/photo-upload";
import { VideoCapture } from "@/components/advanced/VideoCapture";

const vehicleTypes: VehicleType[] = ["Motorcycle", "Scooter", "3W", "4W"];
const angles: CaptureAngle[] = ["Front", "Rear", "Left", "Right", "Top", "Interior", "Engine"];

const schema = z.object({
  plate: z.string().min(4, "Plate number required"),
  model: z.string().min(2, "Model required"),
  vin: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function NewInspectionPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [vehicleType, setVehicleType] = useState<VehicleType>("4W");
  const [selectedAngles, setSelectedAngles] = useState<CaptureAngle[]>(["Front"]);
  const { selectedFile, setFile, setVehicleInfo, setAngles } = useInspectionStore();
  const { register, handleSubmit, formState: { errors }, getValues } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const angleCoverageWarning = useMemo(() => (
    selectedAngles.length < 3 ? "Insufficient angle coverage. Capture at least 3 angles for reliable AI output." : ""
  ), [selectedAngles]);

  const submitInspection = () => {
    const values = getValues();
    if (!selectedFile) return;
    setVehicleInfo({ vehicleType, plate: values.plate, model: values.model, vin: values.vin });
    setAngles(selectedAngles);
    navigate("/inspection/processing");
  };

  return (
    <div className="space-y-4">
      <Card>
        <p className="text-lg font-semibold text-slate-100">New Inspection</p>
        <p className="text-sm text-slate-400">Fast guided flow for one-thumb field usage.</p>
        <div className="mt-3"><InspectionStepper steps={["Vehicle", "Details", "Angles", "Upload"]} activeStep={step} /></div>
      </Card>

      {step === 0 ? (
        <Card className="space-y-3">
          <Label>Select vehicle type</Label>
          <div className="grid grid-cols-2 gap-2">
            {vehicleTypes.map((type) => (
              <button key={type} type="button" onClick={() => setVehicleType(type)} className={`rounded-xl border px-3 py-2 text-sm ${vehicleType === type ? "border-cyan-300 bg-cyan-400/10 text-cyan-100" : "border-white/15 text-slate-300"}`}>{type}</button>
            ))}
          </div>
          <Button className="w-full" onClick={() => setStep(1)}>Continue</Button>
        </Card>
      ) : null}

      {step === 1 ? (
        <Card className="space-y-3">
          <div>
            <Label htmlFor="plate">Plate Number</Label>
            <Input id="plate" placeholder="MH12AB9087" {...register("plate")} />
            {errors.plate ? <p className="mt-1 text-xs text-rose-300">{errors.plate.message}</p> : null}
          </div>
          <div>
            <Label htmlFor="model">Vehicle Model</Label>
            <Input id="model" placeholder="Hyundai i20" {...register("model")} />
            {errors.model ? <p className="mt-1 text-xs text-rose-300">{errors.model.message}</p> : null}
          </div>
          <div>
            <Label htmlFor="vin">VIN (optional)</Label>
            <Input id="vin" placeholder="MA3EHKD17A1234567" {...register("vin")} />
          </div>
          <Button className="w-full" onClick={handleSubmit(() => setStep(2))}>Continue</Button>
        </Card>
      ) : null}

      {step === 2 ? (
        <Card className="space-y-3">
          <Label>Capture angles</Label>
          <div className="flex flex-wrap gap-2">
            {angles.map((angle) => {
              const active = selectedAngles.includes(angle);
              return (
                <button key={angle} type="button" onClick={() => setSelectedAngles((prev) => prev.includes(angle) ? prev.filter((item) => item !== angle) : [...prev, angle])} className={`rounded-full border px-3 py-1 text-xs ${active ? "border-cyan-300 bg-cyan-400/10 text-cyan-100" : "border-white/15 text-slate-300"}`}>{angle}</button>
              );
            })}
          </div>
          {angleCoverageWarning ? <Badge className="border-amber-400/30 bg-amber-400/10 text-amber-200">{angleCoverageWarning}</Badge> : null}
          <Button className="w-full" onClick={() => setStep(3)}>Continue</Button>
        </Card>
      ) : null}

      {step === 3 ? (
        <div className="space-y-4">
          <PhotoUpload file={selectedFile} onFileChange={setFile} />
          <VideoCapture onVideoReady={(blob) => setFile(new File([blob], `capture-${Date.now()}.webm`, { type: blob.type || "video/webm" }))} onCapture={(videoFile) => setFile(videoFile)} />
          <div className="sticky bottom-16 space-y-2 md:bottom-4">
            <Button className="w-full" disabled={!selectedFile} onClick={submitInspection}>Analyze Damage</Button>
            {!selectedFile ? <p className="text-center text-xs text-slate-400">Upload at least one image to continue.</p> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
