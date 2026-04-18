import pytest
from itertools import product

from app.services.dsq_v2 import compute_dsq_v2


def _finding(
    *,
    cls: str = "dent",
    severity: str = "medium",
    confidence: float = 0.7,
    box: list[float] | None = None,
    use_type_key: bool = False,
):
    payload = {
        "severity": severity,
        "confidence": confidence,
        "box": box or [0, 0, 200, 200],
    }
    payload["type" if use_type_key else "class"] = cls
    return payload


def test_empty_findings_returns_zero_score_and_auto_approve():
    result = compute_dsq_v2([])
    assert result.score == 0.0
    assert result.overall_severity == "low"
    assert result.auto_approve is True


def test_small_low_confidence_damage_stays_low_band():
    findings = [
        {
            "class": "scratch",
            "severity": "low",
            "confidence": 0.4,
            "box": [0, 0, 20, 20],
        }
    ]
    result = compute_dsq_v2(findings, (720, 1280, 3))
    assert result.score < 34
    assert result.overall_severity == "low"
    assert result.repair_cost_min_inr == 2000


def test_large_high_severity_damage_enters_high_band():
    findings = [
        {
            "class": "broken part",
            "severity": "high",
            "confidence": 0.95,
            "box": [0, 0, 1000, 600],
        },
        {
            "class": "dent",
            "severity": "high",
            "confidence": 0.9,
            "box": [100, 100, 900, 650],
        },
    ]
    result = compute_dsq_v2(findings, (720, 1280, 3))
    assert result.score >= 67
    assert result.overall_severity == "high"
    assert result.auto_approve is False
    assert result.repair_cost_min_inr == 20000


def test_unknown_detection_type_falls_back_without_crashing():
    findings = [
        {
            "class": "mystery-damage",
            "severity": "medium",
            "confidence": 0.8,
            "box": [0, 0, 300, 300],
        }
    ]
    result = compute_dsq_v2(findings, (720, 1280, 3))
    assert result.score > 0


def test_invalid_box_dimensions_are_handled_safely():
    findings = [
        {
            "class": "dent",
            "severity": "high",
            "confidence": 0.8,
            "box": [100, 100, 90, 80],
        },
        {"class": "dent", "severity": "high", "confidence": 0.8, "box": []},
    ]
    result = compute_dsq_v2(findings, (720, 1280, 3))
    assert result.score >= 0


def test_confidence_is_clamped_to_valid_range():
    findings = [
        {
            "class": "dent",
            "severity": "medium",
            "confidence": 10.0,
            "box": [0, 0, 100, 100],
        },
        {
            "class": "dent",
            "severity": "medium",
            "confidence": -2.0,
            "box": [0, 0, 100, 100],
        },
    ]
    result = compute_dsq_v2(findings, (720, 1280, 3))
    assert 0 <= result.score <= 100


def test_fraud_score_tracks_dsq_and_is_bounded():
    findings = [
        {
            "class": "crack",
            "severity": "high",
            "confidence": 1.0,
            "box": [0, 0, 1280, 720],
        }
    ]
    result = compute_dsq_v2(findings, (720, 1280, 3))
    assert 0 <= result.fraud_risk_score <= 100
    assert result.fraud_risk_score >= 40


def test_breakdown_components_are_present_and_normalized():
    findings = [
        {
            "class": "scratch",
            "severity": "medium",
            "confidence": 0.7,
            "box": [0, 0, 200, 200],
        }
    ]
    result = compute_dsq_v2(findings, (720, 1280, 3))
    assert set(result.breakdown.keys()) == {
        "area_ratio",
        "part_criticality",
        "functional_impact",
        "confidence",
    }
    assert all(0 <= value <= 1 for value in result.breakdown.values())


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        ("low", "low"),
        ("medium", "medium"),
        ("high", "high"),
        ("invalid", "medium"),
        ("", "medium"),
    ],
)
def test_severity_normalization_is_safe(severity: str, expected: str):
    result = compute_dsq_v2([_finding(severity=severity)], (720, 1280, 3))
    baseline = compute_dsq_v2([_finding(severity=expected)], (720, 1280, 3))
    assert result.score == baseline.score


@pytest.mark.parametrize(
    "damage_type",
    ["unknown", "foo", "panel warp", ""],
)
def test_unknown_damage_types_fallback_to_paint_damage(damage_type: str):
    result = compute_dsq_v2([_finding(cls=damage_type)], (720, 1280, 3))
    baseline = compute_dsq_v2([_finding(cls="paint damage")], (720, 1280, 3))
    assert result.score == baseline.score


def test_score_is_capped_to_hundred_even_for_extreme_findings():
    findings = [
        _finding(
            cls="broken part", severity="high", confidence=1.0, box=[0, 0, 5000, 5000]
        )
    ] * 20
    result = compute_dsq_v2(findings, (720, 1280, 3))
    assert result.score == 100.0


def test_fraud_risk_formula_matches_expected_ratio():
    findings = [
        _finding(cls="dent", severity="high", confidence=0.9, box=[0, 0, 700, 700])
    ]
    result = compute_dsq_v2(findings, (720, 1280, 3))
    assert result.fraud_risk_score == round(min(100.0, result.score * 0.62), 2)


def test_same_finding_scores_higher_on_smaller_image_shape():
    finding = _finding(
        cls="dent", severity="high", confidence=0.7, box=[0, 0, 300, 300]
    )
    small = compute_dsq_v2([finding], (300, 300, 3))
    large = compute_dsq_v2([finding], (1200, 1600, 3))
    assert small.score >= large.score


def test_higher_confidence_increases_score_for_same_area():
    low_conf = compute_dsq_v2([_finding(confidence=0.2)], (720, 1280, 3))
    high_conf = compute_dsq_v2([_finding(confidence=0.9)], (720, 1280, 3))
    assert high_conf.score > low_conf.score


def test_type_key_and_class_key_both_supported():
    class_based = compute_dsq_v2(
        [_finding(cls="crack", use_type_key=False)], (720, 1280, 3)
    )
    type_based = compute_dsq_v2(
        [_finding(cls="crack", use_type_key=True)], (720, 1280, 3)
    )
    assert class_based.score == type_based.score


def test_missing_confidence_defaults_to_zero_without_crash():
    finding = _finding()
    finding.pop("confidence")
    result = compute_dsq_v2([finding], (720, 1280, 3))
    assert 0 <= result.score <= 100


def test_overall_severity_bands_align_with_score_ranges():
    low = compute_dsq_v2(
        [_finding(cls="scratch", severity="low", confidence=0.1, box=[0, 0, 20, 20])],
        (720, 1280, 3),
    )
    medium = compute_dsq_v2(
        [_finding(cls="dent", severity="medium", confidence=1.0, box=[0, 0, 900, 700])],
        (720, 1280, 3),
    )
    high = compute_dsq_v2(
        [
            _finding(
                cls="broken part",
                severity="high",
                confidence=1.0,
                box=[0, 0, 1280, 720],
            )
        ],
        (720, 1280, 3),
    )
    assert low.score < 34 and low.overall_severity == "low"
    assert 34 <= medium.score < 67 and medium.overall_severity == "medium"
    assert high.score >= 67 and high.overall_severity == "high"


def test_auto_approve_flag_matches_score_threshold():
    low = compute_dsq_v2(
        [_finding(cls="scratch", severity="low", confidence=0.1, box=[0, 0, 20, 20])],
        (720, 1280, 3),
    )
    high = compute_dsq_v2(
        [
            _finding(
                cls="broken part",
                severity="high",
                confidence=1.0,
                box=[0, 0, 1280, 720],
            )
        ],
        (720, 1280, 3),
    )
    assert low.auto_approve is True
    assert high.auto_approve is False
    assert low.auto_approve == (low.score < 45)
    assert high.auto_approve == (high.score < 45)


def test_repair_cost_bands_follow_score_range():
    low = compute_dsq_v2(
        [_finding(cls="scratch", severity="low", confidence=0.2, box=[0, 0, 20, 20])],
        (720, 1280, 3),
    )
    medium = compute_dsq_v2(
        [_finding(cls="dent", severity="medium", confidence=1.0, box=[0, 0, 900, 700])],
        (720, 1280, 3),
    )
    high = compute_dsq_v2(
        [
            _finding(
                cls="broken part",
                severity="high",
                confidence=1.0,
                box=[0, 0, 1280, 720],
            )
        ],
        (720, 1280, 3),
    )

    assert low.repair_cost_min_inr == 2000 and low.repair_cost_max_inr == 7000
    assert medium.repair_cost_min_inr == 8000 and medium.repair_cost_max_inr == 22000
    assert high.repair_cost_min_inr == 20000 and high.repair_cost_max_inr == 55000


def test_breakdown_sum_tracks_score_normalization():
    result = compute_dsq_v2(
        [_finding(cls="dent", severity="high", confidence=0.9, box=[0, 0, 500, 500])],
        (720, 1280, 3),
    )
    total = sum(result.breakdown.values())
    normalized = round(min(100.0, result.score) / 100.0, 4)
    assert abs(total - normalized) <= 0.001


MATRIX_DAMAGE_TYPES = ["scratch", "dent", "crack", "broken part", "paint damage"]
MATRIX_SEVERITIES = ["low", "medium", "high"]
MATRIX_CONFIDENCES = [0.1, 0.5, 0.9]
MATRIX_BOXES = [[0, 0, 20, 20], [0, 0, 240, 240], [0, 0, 900, 700], [0, 0, 1280, 720]]

DSQ_MATRIX_CASES = [
    {
        "cls": cls,
        "severity": severity,
        "confidence": confidence,
        "box": box,
    }
    for cls, severity, confidence, box in product(
        MATRIX_DAMAGE_TYPES, MATRIX_SEVERITIES, MATRIX_CONFIDENCES, MATRIX_BOXES
    )
][:47]


@pytest.mark.parametrize("case", DSQ_MATRIX_CASES)
def test_dsq_v2_47_case_matrix_contract(case: dict):
    result = compute_dsq_v2(
        [
            _finding(
                cls=case["cls"],
                severity=case["severity"],
                confidence=case["confidence"],
                box=case["box"],
            )
        ],
        (720, 1280, 3),
    )
    assert 0 <= result.score <= 100
    assert result.overall_severity in {"low", "medium", "high"}
    assert 0 <= result.fraud_risk_score <= 100
    assert result.repair_cost_min_inr <= result.repair_cost_max_inr
    assert set(result.breakdown.keys()) == {
        "area_ratio",
        "part_criticality",
        "functional_impact",
        "confidence",
    }
