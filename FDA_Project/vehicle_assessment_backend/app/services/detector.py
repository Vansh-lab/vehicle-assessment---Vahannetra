import os
from ultralytics import YOLO

class DamageDetector:
    def __init__(self):
        # Path issue fix karne ke liye 'r' (raw string) use kiya hai
        model_path = r"D:\FDA_Project\vehicle_assessment_backend\app\models\best.pt"
        self.model = YOLO(model_path)

    def analyze_vehicle(self, file_path):
        # 1. AI Inference (AI se check karwana)
        results = self.model(file_path)
        
        # 2. Processed Image Save karna (jisme boxes honge)
        # File name ke aage '_detected' jod dega
        base, ext = os.path.splitext(file_path)
        output_path = f"{base}_detected{ext}"
        results[0].save(filename=output_path)
        
        # 3. Detections ko list mein convert karna
        detections = []
        for r in results:
            for box in r.boxes:
                detections.append({
                    "class": self.model.names[int(box.cls)],
                    "confidence": round(float(box.conf), 2),
                    "box": box.xyxy[0].tolist() # [x1, y1, x2, y2]
                })
        
        return detections, output_path