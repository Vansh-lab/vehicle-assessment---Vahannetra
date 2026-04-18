from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from pathlib import Path
from typing import Any

import cv2


@dataclass
class VideoFrame:
    sharpness: float
    timestamp_sec: int
    frame_path: Path


@dataclass
class VideoExtractionResult:
    duration_seconds: int
    fps: float
    extracted_frames: list[VideoFrame]


def extract_best_frames(
    video_path: Path,
    output_dir: Path,
    n_frames: int = 6,
    sharpness_threshold: float = 100.0,
) -> VideoExtractionResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        return VideoExtractionResult(duration_seconds=0, fps=0.0, extracted_frames=[])

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0:
        fps = 1.0
    step = max(1, int(round(fps)))
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_seconds = int(total_frames / fps) if total_frames > 0 else 0

    top_candidates: list[tuple[float, int, Any]] = []
    frame_index = 0
    while capture.isOpened():
        ok, frame = capture.read()
        if not ok:
            break
        if frame_index % step == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            if sharpness > sharpness_threshold:
                timestamp_sec = int(frame_index / fps)
                candidate = (sharpness, timestamp_sec, frame.copy())
                if len(top_candidates) < n_frames:
                    heappush(top_candidates, candidate)
                elif top_candidates[0][0] < sharpness:
                    heappop(top_candidates)
                    heappush(top_candidates, candidate)
        frame_index += 1
    capture.release()

    selected = sorted(top_candidates, key=lambda item: item[0], reverse=True)

    extracted: list[VideoFrame] = []
    for idx, (sharpness, timestamp_sec, frame) in enumerate(selected):
        frame_path = output_dir / f"frame_{idx + 1}.jpg"
        cv2.imwrite(str(frame_path), frame)
        extracted.append(
            VideoFrame(
                sharpness=sharpness, timestamp_sec=timestamp_sec, frame_path=frame_path
            )
        )

    return VideoExtractionResult(
        duration_seconds=duration_seconds, fps=fps, extracted_frames=extracted
    )
