import { create } from "zustand";
import type { CaptureAngle, InspectionResult, VehicleType } from "@/types/domain";

interface InspectionState {
  vehicleType: VehicleType;
  plate: string;
  model: string;
  vin?: string;
  selectedAngles: CaptureAngle[];
  selectedFile: File | null;
  latestResult: InspectionResult | null;
  setVehicleInfo: (value: { vehicleType: VehicleType; plate: string; model: string; vin?: string }) => void;
  setAngles: (angles: CaptureAngle[]) => void;
  setFile: (file: File | null) => void;
  setResult: (result: InspectionResult | null) => void;
  reset: () => void;
}

const initialState = {
  vehicleType: "4W" as VehicleType,
  plate: "",
  model: "",
  vin: "",
  selectedAngles: ["Front"] as CaptureAngle[],
  selectedFile: null,
  latestResult: null,
};

export const useInspectionStore = create<InspectionState>((set) => ({
  ...initialState,
  setVehicleInfo: ({ vehicleType, plate, model, vin }) => set({ vehicleType, plate, model, vin }),
  setAngles: (selectedAngles) => set({ selectedAngles }),
  setFile: (selectedFile) => set({ selectedFile }),
  setResult: (latestResult) => set({ latestResult }),
  reset: () => set(initialState),
}));
