from __future__ import annotations

from dataclasses import dataclass

SEVERITY_WEIGHTS = {"low": 0.35, "medium": 0.65, "high": 1.0}
TYPE_WEIGHTS = {
    "scratch": 0.4,
    "dent": 0.7,
    "crack": 0.8,
    "broken part": 1.0,
    "paint damage": 0.5,
}


@dataclass(frozen=True)
class DSQv2Result:
    score: float
    breakdown: dict[str, float]
    overall_severity: str
    fraud_risk_score: float
    auto_approve: bool
    repair_cost_min_inr: int
    repair_cost_max_inr: int


def _normalized_detection_type(raw_name: str) -> str:
    normalized = (raw_name or "").strip().lower()
    return normalized if normalized in TYPE_WEIGHTS else "paint damage"


def _normalized_severity(raw_severity: str) -> str:
    normalized = (raw_severity or "").strip().lower()
    return normalized if normalized in SEVERITY_WEIGHTS else "medium"


def _box_area(box: list[float]) -> float:
    if len(box) < 4:
        return 0.0
    width = max(0.0, float(box[2]) - float(box[0]))
    height = max(0.0, float(box[3]) - float(box[1]))
    return width * height


def _score_to_severity(score: float) -> str:
    if score >= 67:
        return "high"
    if score >= 34:
        return "medium"
    return "low"


def _repair_cost_band(score: float) -> tuple[int, int]:
    if score < 34:
        return (2000, 7000)
    if score < 67:
        return (8000, 22000)
    return (20000, 55000)


def _component_breakdown(score: float) -> dict[str, float]:
    normalized = max(0.0, min(100.0, score)) / 100.0
    return {
        "area_ratio": round(normalized * 0.35, 4),
        "part_criticality": round(normalized * 0.3, 4),
        "functional_impact": round(normalized * 0.25, 4),
        "confidence": round(normalized * 0.1, 4),
    }


def compute_dsq_v2(
    findings: list[dict], image_shape: tuple[int, int, int] = (720, 1280, 3)
) -> DSQv2Result:
    if not findings:
        return DSQv2Result(
            score=0.0,
            breakdown=_component_breakdown(0.0),
            overall_severity="low",
            fraud_risk_score=0.0,
            auto_approve=True,
            repair_cost_min_inr=2000,
            repair_cost_max_inr=7000,
        )

    height, width = image_shape[:2]
    image_area = max(1.0, float(height * width))

    weighted_area = 0.0
    confidence_values: list[float] = []
    for item in findings:
        det_type = _normalized_detection_type(
            str(item.get("type") or item.get("class") or "")
        )
        severity = _normalized_severity(str(item.get("severity") or "medium"))
        area = _box_area(item.get("box", []))
        type_weight = TYPE_WEIGHTS[det_type]
        severity_weight = SEVERITY_WEIGHTS[severity]
        weighted_area += area * type_weight * severity_weight

        confidence = float(item.get("confidence", 0.0))
        confidence_values.append(max(0.0, min(1.0, confidence)))

    area_ratio = min(1.0, weighted_area / image_area)
    avg_confidence = (
        sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
    )

    score = round(min(100.0, (area_ratio * 85.0) + (avg_confidence * 15.0)), 2)
    fraud_risk_score = round(min(100.0, score * 0.62), 2)
    auto_approve = score < 45
    cost_min, cost_max = _repair_cost_band(score)

    return DSQv2Result(
        score=score,
        breakdown=_component_breakdown(score),
        overall_severity=_score_to_severity(score),
        fraud_risk_score=fraud_risk_score,
        auto_approve=auto_approve,
        repair_cost_min_inr=cost_min,
        repair_cost_max_inr=cost_max,
    )
