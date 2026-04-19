import { create } from "zustand";
import type { CaptureAngle, InspectionResult, VehicleType } from "@/types/domain";

interface InspectionState {
  vehicleType: VehicleType;
  plate: string;
  model: string;
  vin?: string;
  selectedAngles: CaptureAngle[];
  selectedFile: File | null;
  beforeFile: File | null;
  afterFile: File | null;
  beforeImageUrl: string | null;
  afterImageUrl: string | null;
  latestResult: InspectionResult | null;
  setVehicleInfo: (value: { vehicleType: VehicleType; plate: string; model: string; vin?: string }) => void;
  setAngles: (angles: CaptureAngle[]) => void;
  setFile: (file: File | null) => void;
  setBeforeAfterFiles: (payload: { beforeFile?: File | null; afterFile?: File | null }) => void;
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
  beforeFile: null,
  afterFile: null,
  beforeImageUrl: null,
  afterImageUrl: null,
  latestResult: null,
};

function revokeBlobUrl(url?: string | null) {
  if (url?.startsWith("blob:")) {
    URL.revokeObjectURL(url);
  }
}

export const useInspectionStore = create<InspectionState>((set) => ({
  ...initialState,
  setVehicleInfo: ({ vehicleType, plate, model, vin }) => set({ vehicleType, plate, model, vin }),
  setAngles: (selectedAngles) => set({ selectedAngles }),
  setFile: (selectedFile) => set({ selectedFile }),
  setBeforeAfterFiles: ({ beforeFile, afterFile }) =>
    set((state) => {
      const nextBeforeFile = beforeFile === undefined ? state.beforeFile : beforeFile;
      const nextAfterFile = afterFile === undefined ? state.afterFile : afterFile;
      const nextBeforeImageUrl = nextBeforeFile ? URL.createObjectURL(nextBeforeFile) : null;
      const nextAfterImageUrl = nextAfterFile ? URL.createObjectURL(nextAfterFile) : null;

      if (state.beforeImageUrl !== nextBeforeImageUrl) revokeBlobUrl(state.beforeImageUrl);
      if (state.afterImageUrl !== nextAfterImageUrl) revokeBlobUrl(state.afterImageUrl);

      return {
        beforeFile: nextBeforeFile,
        afterFile: nextAfterFile,
        beforeImageUrl: nextBeforeImageUrl,
        afterImageUrl: nextAfterImageUrl,
      };
    }),
  setResult: (latestResult) =>
    set((state) => {
      if (state.latestResult?.processedImageUrl !== latestResult?.processedImageUrl) {
        revokeBlobUrl(state.latestResult?.processedImageUrl);
      }
      return { latestResult };
    }),
  reset: () =>
    set((state) => {
      revokeBlobUrl(state.latestResult?.processedImageUrl);
      revokeBlobUrl(state.beforeImageUrl);
      revokeBlobUrl(state.afterImageUrl);
      return initialState;
    }),
}));
