from __future__ import annotations

from dataclasses import dataclass

SEVERITY_WEIGHTS = {"low": 0.6, "medium": 0.8, "high": 1.0}
TYPE_WEIGHTS = {
    "scratch": 0.35,
    "dent": 0.65,
    "crack": 0.8,
    "broken part": 1.0,
    "paint damage": 0.45,
}
PART_CRITICALITY = {
    "windshield": 0.9,
    "battery_casing": 1.0,
    "engine_bay": 0.95,
    "door_panel": 0.35,
    "bumper": 0.5,
    "fender": 0.45,
}
FUNCTIONAL_BY_TYPE = {
    "scratch": 0.2,
    "paint damage": 0.25,
    "dent": 0.55,
    "crack": 0.85,
    "broken part": 1.0,
}

# Required DSQ expression:
# Σ [w1*area + w2*criticality + w3*functional + w4*confidence] * 100
W_AREA = 0.35
W_CRITICALITY = 0.30
W_FUNCTIONAL = 0.20
W_CONFIDENCE = 0.15


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


def _part_criticality(item: dict, damage_type: str) -> float:
    part = str(item.get("part") or item.get("part_name") or "").strip().lower()
    if part in PART_CRITICALITY:
        return PART_CRITICALITY[part]
    # Fallback from damage type if part is unknown
    return TYPE_WEIGHTS.get(damage_type, 0.45)


def _normalize_breakdown(total_components: dict[str, float]) -> dict[str, float]:
    total = sum(total_components.values())
    if total <= 0:
        return {
            "area_ratio": 0.0,
            "part_criticality": 0.0,
            "functional_impact": 0.0,
            "confidence": 0.0,
        }
    normalized_total = min(1.0, total)
    scale = normalized_total / total
    return {
        "area_ratio": round(total_components["area_ratio"] * scale, 4),
        "part_criticality": round(total_components["part_criticality"] * scale, 4),
        "functional_impact": round(total_components["functional_impact"] * scale, 4),
        "confidence": round(total_components["confidence"] * scale, 4),
    }


def compute_dsq_v2(
    findings: list[dict], image_shape: tuple[int, int, int] = (720, 1280, 3)
) -> DSQv2Result:
    if not findings:
        return DSQv2Result(
            score=0.0,
            breakdown={
                "area_ratio": 0.0,
                "part_criticality": 0.0,
                "functional_impact": 0.0,
                "confidence": 0.0,
            },
            overall_severity="low",
            fraud_risk_score=0.0,
            auto_approve=True,
            repair_cost_min_inr=2000,
            repair_cost_max_inr=7000,
        )

    height, width = image_shape[:2]
    image_area = max(1.0, float(height * width))

    component_totals = {
        "area_ratio": 0.0,
        "part_criticality": 0.0,
        "functional_impact": 0.0,
        "confidence": 0.0,
    }

    for item in findings:
        damage_type = _normalized_detection_type(str(item.get("type") or item.get("class") or ""))
        severity = _normalized_severity(str(item.get("severity") or "medium"))
        severity_factor = SEVERITY_WEIGHTS[severity]

        raw_area_ratio = min(1.0, max(0.0, _box_area(item.get("box", [])) / image_area))
        area_ratio = raw_area_ratio * TYPE_WEIGHTS[damage_type]
        criticality = _part_criticality(item, damage_type)
        functional = FUNCTIONAL_BY_TYPE[damage_type]
        confidence = max(0.0, min(1.0, float(item.get("confidence", 0.0))))

        component_totals["area_ratio"] += W_AREA * area_ratio * severity_factor
        component_totals["part_criticality"] += W_CRITICALITY * criticality * severity_factor
        component_totals["functional_impact"] += W_FUNCTIONAL * functional * severity_factor
        component_totals["confidence"] += W_CONFIDENCE * confidence * severity_factor

    breakdown = _normalize_breakdown(component_totals)
    normalized_score = min(1.0, sum(component_totals.values()))
    score = round(normalized_score * 100.0, 2)
    fraud_risk_score = round(min(100.0, score * 0.62), 2)
    auto_approve = score < 45
    cost_min, cost_max = _repair_cost_band(score)

    return DSQv2Result(
        score=score,
        breakdown=breakdown,
        overall_severity=_score_to_severity(score),
        fraud_risk_score=fraud_risk_score,
        auto_approve=auto_approve,
        repair_cost_min_inr=cost_min,
        repair_cost_max_inr=cost_max,
    )
