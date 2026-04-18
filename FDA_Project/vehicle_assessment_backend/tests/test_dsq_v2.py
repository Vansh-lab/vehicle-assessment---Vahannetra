from app.services.dsq_v2 import compute_dsq_v2


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
