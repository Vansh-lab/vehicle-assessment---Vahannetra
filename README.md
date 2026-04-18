# AI Vehicle Assessment Backend

This is a FastAPI-based backend service designed to automatically assess vehicle damage using AI. It processes uploaded images of vehicles, detects damages like dents and scratches using a YOLO model, calculates a Damage Severity Index (DSI), and provides a triage categorization.

## Features
* **FastAPI Powered**: Fast and interactive API endpoints.
* **YOLOv8 Integration**: Uses a custom-trained Ultralytics YOLO model (`best.pt`) to detect damage.
* **Damage Severity Index (DSI)**: Calculates the severity of damage by comparing the bounding box areas of the detected damages against the total image area.
* **Triage Logic**: Automatically categorizes damage as `COSMETIC` or `STRUCTURAL/FUNCTIONAL` based on the DSI score.

## Project Structure
* `app/main.py`: The main FastAPI application routing and API definitions.
* `app/services/detector.py`: Handles the Ultralytics YOLO model inference and saving processed images.
* `app/utils/assessment.py`: Contains the logic for calculating the Damage Severity Index (DSI).
* `uploads/`: Directory where uploaded and AI-processed images are stored locally.

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone <your-github-repo-url>
   cd vehicle_assessment_backend
   ```

2. **Create a virtual environment (Optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**
   You will need FastAPI, Uvicorn, Ultralytics, OpenCV, and python-multipart.
   ```bash
   pip install fastapi uvicorn ultralytics opencv-python python-multipart
   ```

4. **Model Configuration:**
   Make sure your trained YOLO model (`best.pt`) is located at the path specified in `app/services/detector.py` (currently set to `D:\FDA_Project\vehicle_assessment_backend\app\models\best.pt`). If you move the project, update this path or use a relative path.

## Running the Application

Start the FastAPI development server using Uvicorn:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. 
You can access the interactive Swagger UI documentation at `http://localhost:8000/docs`.

## API Endpoints
* `GET /`: Health check endpoint.
* `POST /assess-damage/`: Upload an image file (`multipart/form-data`) to get an AI damage assessment, DSI score, and a link to the processed image.
* `GET /view-result/{filename}`: View a specific processed image from the `uploads/` directory.

## Deployment & Phase Closure References

- AWS live runtime proof runbook: `FDA_Project/aws-runtime-proof-runbook.md`
- Phase closure audit (closed vs remaining external blockers): `FDA_Project/phase-c-closure-audit.md`
