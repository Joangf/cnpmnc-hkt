from app.services.recommendation import RuleRow, SymptomTerms, match_free_text, score_specialties

RULES = [
    RuleRow(symptom_id=1, specialty_id=10, weight=1.0),  # cough -> respiratory
    RuleRow(symptom_id=1, specialty_id=20, weight=0.3),  # cough -> general
    RuleRow(symptom_id=2, specialty_id=10, weight=1.0),  # breathless -> respiratory
    RuleRow(symptom_id=2, specialty_id=30, weight=0.6),  # breathless -> cardiology
    RuleRow(symptom_id=3, specialty_id=40, weight=1.0),  # rash -> dermatology
]


def test_scores_are_summed_and_sorted() -> None:
    result = score_specialties({1, 2}, RULES)
    assert [r.specialty_id for r in result] == [10, 30, 20]
    assert result[0].score == 2.0
    assert sorted(result[0].symptom_ids) == [1, 2]


def test_unselected_symptoms_are_ignored() -> None:
    assert [r.specialty_id for r in score_specialties({3}, RULES)] == [40]
    assert score_specialties(set(), RULES) == []


def test_free_text_matches_whole_words_case_insensitively() -> None:
    symptoms = [
        SymptomTerms(1, ("Persistent cough", "cough")),
        SymptomTerms(3, ("Skin rash", "rash")),
    ]
    assert match_free_text("I have had a bad COUGH for a week", symptoms) == {1}
    assert match_free_text("I was in a car crash", symptoms) == set()  # 'rash' inside 'crash'
    assert match_free_text("itchy rash and cough", symptoms) == {1, 3}
