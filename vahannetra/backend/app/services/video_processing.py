from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


@dataclass
class ExtractedFrame:
    frame_path: Path
    sharpness: float


@dataclass
class ExtractionResult:
    duration_seconds: int
    frames: list[ExtractedFrame]


def extract_best_frames(
    video_path: Path,
    output_dir: Path,
    n_frames: int = 6,
    sharpness_threshold: float = 100.0,
) -> ExtractionResult:
    output_dir.mkdir(parents=True, exist_ok=True)

    if cv2 is None:
        return ExtractionResult(duration_seconds=0, frames=[])

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        return ExtractionResult(duration_seconds=0, frames=[])

    fps = max(1, int(capture.get(cv2.CAP_PROP_FPS) or 1))
    frame_index = 0
    ranked_frames: list[tuple[float, NDArray[np.uint8]]] = []

    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_seconds = int(total_frames / fps) if fps > 0 and total_frames > 0 else 0

    while capture.isOpened():
        ok, frame = capture.read()
        if not ok:
            break

        if frame_index % fps == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            if sharpness > sharpness_threshold:
                ranked_frames.append((sharpness, frame.copy()))
        frame_index += 1

    capture.release()
    ranked_frames.sort(key=lambda item: item[0], reverse=True)

    extracted: list[ExtractedFrame] = []
    for index, (sharpness, frame) in enumerate(ranked_frames[:n_frames], start=1):
        frame_path = output_dir / f"frame_{index}.jpg"
        cv2.imwrite(str(frame_path), frame)
        extracted.append(ExtractedFrame(frame_path=frame_path, sharpness=sharpness))

    return ExtractionResult(duration_seconds=duration_seconds, frames=extracted)
