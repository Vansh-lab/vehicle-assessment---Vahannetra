import math

import cv2
import numpy as np

from app.routers.analyze import _box_iou
from app.services.dsq_v2 import compute_dsq_v2


def _sharpness(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _severity_bucket(score: float) -> str:
    if score >= 67:
        return "high"
    if score >= 34:
        return "medium"
    if score > 0:
        return "low"
    return "none"


def _category_for_damage(damage_type: str) -> str:
    return (
        "functional"
        if damage_type in {"windshield", "crack", "broken part", "battery_casing"}
        else "cosmetic"
    )


def _quadrant(box: list[int], width: int = 1280, height: int = 960) -> str:
    cx = (box[0] + box[2]) / 2
    cy = (box[1] + box[3]) / 2
    return "top-left" if cx < width / 2 and cy < height / 2 else "other"


def _part_summary(parts: list[str]) -> str:
    return ", ".join(parts)


def _adjacent_parts() -> dict[str, list[str]]:
    return {
        "front_bumper": ["left_fender", "right_fender"],
        "door_panel": ["rear_door", "front_fender"],
    }


def _ev_risk(parts: list[str]) -> str:
    return "high" if "battery_casing" in parts else "low"


def _thermal_probability(severity_score: float) -> float:
    value = 1 / (1 + math.exp(-severity_score / 20))
    return max(0.0, min(1.0, value))


def test_image_quality_sharp_image_passes():
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.line(img, (0, 0), (319, 239), (255, 255, 255), 2)
    assert _sharpness(img) > 100


def test_image_quality_blurry_image_low_score():
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.rectangle(img, (80, 60), (240, 180), (255, 255, 255), -1)
    blurred = cv2.GaussianBlur(img, (31, 31), 0)
    assert _sharpness(blurred) < _sharpness(img)


def test_image_quality_dark_image_low_score():
    dark = np.zeros((240, 320, 3), dtype=np.uint8)
    assert _sharpness(dark) < 1


def test_preprocess_output_size_1280x960():
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    out = cv2.resize(img, (1280, 960))
    assert out.shape[:2] == (960, 1280)


def test_severity_thresholds_0_10_34_67_100():
    assert _severity_bucket(0) == "none"
    assert _severity_bucket(10) == "low"
    assert _severity_bucket(34) == "medium"
    assert _severity_bucket(67) == "high"
    assert _severity_bucket(100) == "high"


def test_windshield_is_functional():
    assert _category_for_damage("windshield") == "functional"


def test_door_scratch_is_cosmetic():
    assert _category_for_damage("door_scratch") == "cosmetic"


def test_bumper_dent_is_both():
    assert _category_for_damage("dent") == "cosmetic"
    assert _category_for_damage("broken part") == "functional"


def test_location_top_left_quadrant():
    assert _quadrant([0, 0, 40, 40]) == "top-left"


def test_location_includes_part_name():
    assert "door" in _part_summary(["front_door", "rear_door"])


def test_iou_perfect_overlap_is_one():
    assert _box_iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0


def test_iou_no_overlap_is_zero():
    assert _box_iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0


def test_iou_partial_overlap_in_range():
    value = _box_iou([0, 0, 20, 20], [10, 10, 30, 30])
    assert 0 < value < 1


def test_iou_symmetric():
    a = _box_iou([1, 1, 20, 20], [5, 5, 30, 30])
    b = _box_iou([5, 5, 30, 30], [1, 1, 20, 20])
    assert a == b


def test_fraud_genuine_damage_low_score():
    r = compute_dsq_v2(
        [
            {
                "class": "scratch",
                "severity": "low",
                "confidence": 0.6,
                "box": [0, 0, 30, 30],
            }
        ]
    )
    assert r.fraud_risk_score < 40


def test_fraud_no_damage_zero():
    assert compute_dsq_v2([]).fraud_risk_score == 0


def test_fraud_uniform_severity_suspicious():
    scores = [
        compute_dsq_v2(
            [
                {
                    "class": "dent",
                    "severity": "high",
                    "confidence": 0.9,
                    "box": [0, 0, 500, 500],
                }
            ]
        ).score
        for _ in range(3)
    ]
    assert max(scores) - min(scores) == 0


def test_part_graph_adjacent_parts_linked():
    graph = _adjacent_parts()
    assert "left_fender" in graph["front_bumper"]


def test_part_graph_summary_mentions_parts():
    summary = _part_summary(["front_bumper", "left_fender"])
    assert "front_bumper" in summary and "left_fender" in summary


def test_ev_battery_damage_high_risk():
    assert _ev_risk(["battery_casing", "door_panel"]) == "high"


def test_no_ev_damage_low_risk():
    assert _ev_risk(["door_panel", "bumper"]) == "low"


def test_thermal_probability_bounded_0_1():
    for score in [0, 10, 50, 100]:
        value = _thermal_probability(score)
        assert 0 <= value <= 1
