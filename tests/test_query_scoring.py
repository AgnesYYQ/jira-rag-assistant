from jirabot.query_scoring import confidence_from_distance, complexity_from_text


def test_confidence_from_distance_is_normalized():
    assert confidence_from_distance(0.0) == 1.0
    assert confidence_from_distance(1.0) == 0.5
    assert confidence_from_distance(3.0) == 0.25


def test_complexity_from_text_returns_score_and_label():
    low_score, low_label = complexity_from_text("return True")
    high_score, high_label = complexity_from_text("\n".join(f"line {i}" for i in range(200)))

    assert 0.0 <= low_score <= 1.0
    assert low_label == "low"
    assert 0.0 <= high_score <= 1.0
    assert high_label in {"medium", "high"}
    assert high_score >= low_score