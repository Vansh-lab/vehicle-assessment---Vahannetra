import os
import shutil
from pathlib import Path

from ultralytics import YOLO


class DamageDetector:
    def __init__(self):
        self.model = None
        self.model_path = Path(__file__).resolve().parent.parent / "models" / "best.pt"

        if self.model_path.exists():
            try:
                self.model = YOLO(str(self.model_path))
            except Exception as error:  # pragma: no cover - environment/model dependent
                print(f"Failed to load YOLO model: {error}")
        else:
            print(f"Model not found at {self.model_path}. Running in fallback mode.")

    def analyze_vehicle(self, file_path: str):
        base, ext = os.path.splitext(file_path)
        output_path = f"{base}_detected{ext}"

        if self.model is None:
            shutil.copy(file_path, output_path)
            return [], output_path

        results = self.model(file_path)
        results[0].save(filename=output_path)

        detections = []
        for result in results:
            for box in result.boxes:
                detections.append(
                    {
                        "class": self.model.names[int(box.cls)],
                        "confidence": round(float(box.conf), 2),
                        "box": box.xyxy[0].tolist(),
                    }
                )

        return detections, output_path
