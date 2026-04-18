from app.services.dsq_v2 import compute_dsq_v2


def _finding(cls: str = "dent", severity: str = "medium", confidence: float = 0.8, box=None, part: str | None = None):
    payload = {
        "class": cls,
        "severity": severity,
        "confidence": confidence,
        "box": box or [0, 0, 200, 200],
    }
    if part:
        payload["part"] = part
    return payload


def test_empty_input_score_zero():
    assert compute_dsq_v2([]).score == 0


def test_windshield_crack_score_gt_60():
    result = compute_dsq_v2([_finding("crack", "high", 0.95, [0, 0, 1280, 600], "windshield")])
    assert result.score > 60


def test_door_scratch_score_lt_30():
    result = compute_dsq_v2([_finding("scratch", "low", 0.55, [0, 0, 80, 40], "door_panel")])
    assert result.score < 30


def test_battery_casing_more_critical_than_door_panel():
    battery = compute_dsq_v2([_finding("crack", "medium", 0.7, [0, 0, 220, 120], "battery_casing")])
    door = compute_dsq_v2([_finding("crack", "medium", 0.7, [0, 0, 220, 120], "door_panel")])
    assert battery.score > door.score


def test_multi_damage_higher_than_single_damage():
    single = compute_dsq_v2([_finding("dent", "medium", 0.7, [0, 0, 180, 180])])
    multi = compute_dsq_v2([
        _finding("dent", "medium", 0.7, [0, 0, 180, 180]),
        _finding("crack", "high", 0.9, [20, 20, 260, 220]),
    ])
    assert multi.score > single.score


def test_breakdown_keys_present():
    result = compute_dsq_v2([_finding()])
    assert set(result.breakdown.keys()) == {"area_ratio", "part_criticality", "functional_impact", "confidence"}


def test_score_capped_at_100():
    result = compute_dsq_v2([_finding("broken part", "high", 1.0, [0, 0, 9999, 9999]) for _ in range(10)])
    assert result.score <= 100


def test_functional_higher_than_cosmetic():
    cosmetic = compute_dsq_v2([_finding("scratch", "medium", 0.9, [0, 0, 220, 220])])
    functional = compute_dsq_v2([_finding("broken part", "medium", 0.9, [0, 0, 220, 220])])
    assert functional.score > cosmetic.score


def test_high_confidence_higher_than_low_confidence():
    low = compute_dsq_v2([_finding("dent", "medium", 0.2)])
    high = compute_dsq_v2([_finding("dent", "medium", 0.95)])
    assert high.score > low.score


def test_safety_critical_parts_scored():
    windshield = compute_dsq_v2([_finding("crack", "medium", 0.8, [0, 0, 160, 100], "windshield")])
    door = compute_dsq_v2([_finding("crack", "medium", 0.8, [0, 0, 160, 100], "door_panel")])
    assert windshield.score > door.score


def test_area_ratio_clamped_0_to_1():
    result = compute_dsq_v2([_finding("dent", "high", 1.0, [0, 0, 9999, 9999])])
    assert 0 <= result.breakdown["area_ratio"] <= 1


def test_part_criticality_boundaries():
    low = compute_dsq_v2([_finding("dent", "medium", 0.8, [0, 0, 140, 80], "door_panel")])
    high = compute_dsq_v2([_finding("dent", "medium", 0.8, [0, 0, 140, 80], "battery_casing")])
    assert high.score > low.score


def test_severity_threshold_boundaries_none_low_medium_high():
    none_case = compute_dsq_v2([])
    low = compute_dsq_v2([_finding("scratch", "low", 0.5, [0, 0, 40, 40])])
    medium = compute_dsq_v2([_finding("dent", "medium", 0.9, [0, 0, 800, 600])])
    high = compute_dsq_v2([_finding("broken part", "high", 1.0, [0, 0, 1280, 720])])
    assert none_case.score == 0
    assert low.overall_severity == "low"
    assert medium.overall_severity in {"medium", "high"}
    assert high.overall_severity == "high"
