from analytics.recommendation_service import RecommendationService
from analytics.topic_result_service import TopicResultService, WeakTopicDetector


def test_topic_thresholds(db):
    service = TopicResultService(db)
    assert service.calculate_weakness_level(49.99, 1) == "high"
    assert service.calculate_weakness_level(50, 1) == "medium"
    assert service.calculate_weakness_level(70, 1) == "low"
    assert service.calculate_weakness_level(85, 1) == "none"
    assert service.calculate_weakness_level(99, 0) == "not_enough_data"


def test_trend_and_stability_boundaries(db):
    service = TopicResultService(db)
    assert service._calculate_progress_trend([50, 65]) == "improving"
    assert service._calculate_progress_trend([65, 50]) == "declining"
    assert service._calculate_progress_trend([50, 64.99]) == "stable"
    assert service._calculate_progress_trend([50]) == "not_enough_data"
    assert service._calculate_stability_index([70, 80]) == 0.9


def test_weak_and_strong_classification(db):
    detector = WeakTopicDetector(db)
    weak = {
        "completed_attempts_count": 2,
        "average_percentage": 55,
        "progress_delta": 5,
        "trend": "stable",
        "completed_lessons_ratio": 1,
        "failed_attempts_count": 1,
        "learning_state": "stagnant",
        "stability_index": 0.9,
    }
    assert detector._is_weak_topic(weak)

    strong = {
        **weak,
        "completed_attempts_count": 3,
        "average_percentage": 90,
        "progress_delta": 2,
        "failed_attempts_count": 0,
        "learning_state": "mastered",
        "completed_lessons_ratio": 1,
    }
    assert detector._is_strong_topic(strong)
    assert not detector._is_weak_topic(strong)


def test_recommendation_rules_and_priority(db):
    service = RecommendationService(db)
    context = {
        "average_percentage": 45,
        "learning_state": "stagnant",
        "risk_level": "high",
        "completed_lessons_ratio": 0.5,
        "completed_attempts_count": 3,
        "progress_delta": 5,
        "trend": "stable",
        "unfinished_lessons_count": 2,
        "failure_streak": 3,
        "stability_index": 0.8,
    }
    keys = [rule.key for rule in service._get_matching_rules(context)]
    assert keys == [
        "high_failure_streak",
        "low_average_score",
        "unfinished_theory",
        "no_progress_after_retries",
    ]
    assert service.determine_priority(context, keys[0]) == "high"
