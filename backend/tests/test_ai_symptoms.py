"""AI symptom search, recommendations and review summaries - with a deterministic fake gateway.

Unit tests need nothing. The pipeline tests run against TEST_DATABASE_URL (pgvector) with a
fake LLM: every word maps to a fixed random unit vector, so a phrase "appears" in a text
exactly when its words do. No real model is ever called.
"""

import hashlib
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.integrations.llm import AIUnavailable
from app.models import Specialty, Symptom, SymptomSpecialtyRule
from app.schemas.symptoms import RecommendationResponse, SpecialtyRecommendation
from app.services import ai_symptoms, review_summary, search_index

DIMS = settings.embedding_dims


def word_vector(word: str) -> np.ndarray:
    seed = int(hashlib.sha256(word.lower().encode()).hexdigest()[:8], 16)
    v = np.random.default_rng(seed).standard_normal(DIMS).astype(np.float32)
    return v / np.linalg.norm(v)


def token_matrix(text: str) -> np.ndarray:
    """One vector per word, then </s> - like bge-m3 ColBERT."""
    words = re.findall(r"\w+", text.lower()) or ["empty"]
    return np.stack([word_vector(w) for w in [*words, "</s>"]])


class FakeLLM:
    def __init__(self, chat_response=None) -> None:
        self.chat_response = chat_response
        self.chat_calls: list[tuple[str, str]] = []

    async def embed(self, texts):
        out = []
        for t in texts:
            m = token_matrix(t).mean(axis=0)
            out.append(m / np.linalg.norm(m))
        return out

    async def embed_colbert(self, texts):
        return [token_matrix(t) for t in texts]

    async def chat_json(self, system, user, *, max_tokens, purpose):
        self.chat_calls.append((purpose, user))
        if isinstance(self.chat_response, Exception):
            raise self.chat_response
        return self.chat_response(user) if callable(self.chat_response) else self.chat_response


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.data:
            return None
        self.data[key] = value
        return True

    async def delete(self, *keys):
        for k in keys:
            self.data.pop(k, None)


# --- unit -----------------------------------------------------------------------------------


def test_clauses_split_on_punctuation_and_joining_words() -> None:
    assert ai_symptoms.clauses("tức ngực, khó thở và hơi sốt") == ["tức ngực", "khó thở", "hơi sốt"]
    assert ai_symptoms.clauses("cough and fever") == ["cough", "fever"]
    assert ai_symptoms.clauses("headache") == ["headache"]


def test_phrase_coverage_is_one_when_every_phrase_word_is_in_the_text() -> None:
    text = token_matrix("i have had chest pain since monday")
    assert ai_symptoms.phrase_coverage(token_matrix("chest pain"), text) == pytest.approx(1.0)
    assert ai_symptoms.phrase_coverage(token_matrix("chest tightness"), text) == pytest.approx(
        0.5, abs=0.06
    )
    assert ai_symptoms.phrase_coverage(token_matrix("skin rash"), text) < 0.1


def test_end_of_text_token_does_not_inflate_short_phrases() -> None:
    text = token_matrix("fever and diarrhoea")
    # "child fever": half its words are in the text; </s> must not count as a match.
    assert ai_symptoms.phrase_coverage(token_matrix("child fever"), text) == pytest.approx(
        0.5, abs=0.06
    )


def test_phrase_present_needs_every_word() -> None:
    assert ai_symptoms.phrase_present("sốt", "nam 17 tuổi tiêu chảy và sốt")
    assert ai_symptoms.phrase_present("mờ mắt", "mắt mờ")  # any order
    assert not ai_symptoms.phrase_present("trẻ bị sốt", "nam 17 tuổi tiêu chảy và sốt")
    assert not ai_symptoms.phrase_present("ho", "họ hàng tôi đến chơi")  # tones matter


def test_rrf_rewards_agreement_between_rankings() -> None:
    scores = ai_symptoms.rrf([[1, 2, 3], [2, 1], [2]], k=60)
    assert max(scores, key=scores.get) == 2
    assert set(scores) == {1, 2, 3}


def test_language_detection() -> None:
    assert ai_symptoms.language_of("tôi bị ho") == "vi"
    assert ai_symptoms.language_of("I have a cough") == "en"
    assert ai_symptoms.language_of(None) == "en"


def _base(*specialty_ids: int) -> RecommendationResponse:
    return RecommendationResponse(
        matched_symptoms=[],
        specialties=[
            SpecialtyRecommendation(specialty_id=i, name=f"S{i}", score=1.0, matched_symptoms=["x"])
            for i in specialty_ids
        ],
        departments=[],
        urgent_warning=None,
        disclaimer="d",
    )


async def test_explanation_keeps_only_specialties_it_was_given(monkeypatch) -> None:
    llm = FakeLLM(
        {
            "summary": "ok",
            "specialties": [
                {"specialty_id": 1, "reason": "because of x"},
                {"specialty_id": 99, "reason": "invented specialty"},
                {"specialty_id": 2, "reason": "  "},
            ],
        }
    )
    monkeypatch.setattr(ai_symptoms, "get_llm", lambda: llm)
    monkeypatch.setattr(ai_symptoms, "redis_client", FakeRedis())
    summary, explanations = await ai_symptoms._explain(_base(1, 2), "cough")
    assert summary == "ok"
    assert [(e.specialty_id, e.reason) for e in explanations] == [(1, "because of x")]


async def test_explanation_is_cached_per_symptom_set(monkeypatch) -> None:
    llm = FakeLLM({"summary": "ok", "specialties": [{"specialty_id": 1, "reason": "r"}]})
    monkeypatch.setattr(ai_symptoms, "get_llm", lambda: llm)
    monkeypatch.setattr(ai_symptoms, "redis_client", FakeRedis())
    await ai_symptoms._explain(_base(1), "cough")
    await ai_symptoms._explain(_base(1), "a different sentence, same language")
    assert len(llm.chat_calls) == 1


class _Review:
    def __init__(self, id, rating, comment):
        self.id, self.rating, self.comment = id, rating, comment


async def test_review_summary_drops_points_without_valid_citations(monkeypatch) -> None:
    llm = FakeLLM(
        {
            "summary": "Mostly positive.",
            "points": [
                {"text": "Clear explanations", "review_ids": [1, 2]},
                {"text": "Invented point", "review_ids": [42]},
                {"text": "No citation", "review_ids": []},
            ],
        }
    )
    monkeypatch.setattr(review_summary, "get_llm", lambda: llm)
    summary, points = await review_summary._generate(
        [_Review(1, 5, "clear"), _Review(2, 4, "very clear")]
    )
    assert summary == "Mostly positive."
    assert points == [{"text": "Clear explanations", "review_ids": [1, 2]}]


def test_review_set_hash_changes_when_a_review_is_hidden() -> None:
    a, b = _Review(1, 5, "good"), _Review(2, 2, "slow")
    assert review_summary.review_set_hash([a, b]) == review_summary.review_set_hash([b, a])
    assert review_summary.review_set_hash([a, b]) != review_summary.review_set_hash([a])


# --- pipeline against PostgreSQL --------------------------------------------------------------

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
db = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")
BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def migrated():
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        check=True,
    )


@pytest.fixture
async def sessions(migrated):
    engine = create_async_engine(TEST_DATABASE_URL, pool_size=5)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def catalog(sessions, monkeypatch):
    """Two symptoms with words unique to this test run, rules to two specialties, indexed."""
    tag = uuid.uuid4().hex[:8]
    llm = FakeLLM()
    monkeypatch.setattr(ai_symptoms, "get_llm", lambda: llm)
    monkeypatch.setattr(search_index, "get_llm", lambda: llm)
    async with sessions() as session:
        cardio = Specialty(name=f"Cardio-{tag}")
        derm = Specialty(name=f"Derm-{tag}")
        chest = Symptom(
            name=f"chest{tag} pain{tag}",
            keywords=f"tight{tag} chest{tag}",
            is_red_flag=True,
            red_flag_message="Chest pain can be serious.",
        )
        rash = Symptom(name=f"skin{tag} rash{tag}", keywords=f"itchy{tag} spots{tag}")
        session.add_all([cardio, derm, chest, rash])
        await session.flush()
        session.add_all(
            [
                SymptomSpecialtyRule(symptom_id=chest.id, specialty_id=cardio.id, weight=1.0),
                SymptomSpecialtyRule(symptom_id=rash.id, specialty_id=derm.id, weight=1.0),
            ]
        )
        await session.commit()
        assert await search_index.sync_index(session)
        ids = {"chest": chest.id, "rash": rash.id, "cardio": cardio.id, "derm": derm.id}
    yield tag, ids, llm
    async with sessions() as session:  # keep later runs' indexes small
        for key in ("chest", "rash"):
            (await session.get(Symptom, ids[key])).is_active = False
        await session.commit()
        await search_index.sync_index(session)


@db
async def test_symptoms_found_in_free_text_with_warning_sign(sessions, catalog) -> None:
    tag, ids, llm = catalog
    async with sessions() as session:
        result = await ai_symptoms.interpret(
            session, f"since monday my chest{tag} feels tight{tag} and I have itchy{tag} spots{tag}"
        )
    found = {s.id for s in result.symptoms}
    assert found == {ids["chest"], ids["rash"]}
    assert all(s.via == "text" and s.score >= settings.ai_gate_min_score for s in result.symptoms)
    assert result.urgent_warning and "Chest pain can be serious." in result.urgent_warning
    assert [s.key for s in result.trace][:4] == ["red_flag_text", "hybrid", "rerank", "gate"]
    assert llm.chat_calls == []  # everything passed the gate: no paid call


@db
async def test_one_shared_word_does_not_pull_in_a_longer_phrase(sessions, catalog) -> None:
    """Regression: "fever" in the text made "child fever" pass on the average score."""
    tag, ids, _ = catalog
    async with sessions() as session:
        result = await ai_symptoms.interpret(session, f"17 year old with spots{tag} only")
    assert [s.id for s in result.symptoms] == []  # "itchy spots" needs both words


@db
async def test_unrelated_text_finds_nothing_and_skips_the_paid_rephrase(sessions, catalog) -> None:
    _, _, llm = catalog
    async with sessions() as session:
        result = await ai_symptoms.interpret(session, "the weather is lovely today")
    assert result.symptoms == []
    assert any(s.key == "rephrase" and s.skipped for s in result.trace)
    assert llm.chat_calls == []


@db
async def test_rephrasing_is_verified_against_the_original_words(
    sessions, catalog, monkeypatch
) -> None:
    tag, ids, llm = catalog
    monkeypatch.setattr(settings, "ai_rephrase_min_best_score", 0.0)
    monkeypatch.setattr(settings, "ai_rephrase_floor_score", 0.4)
    # The patient wrote one of the two words; the rephrasing supplies the catalog phrase.
    llm.chat_response = {"variants": [f"skin{tag} rash{tag}", f"chest{tag} pain{tag}"]}
    async with sessions() as session:
        result = await ai_symptoms.interpret(session, f"weird rash{tag} today")
    # rash: 0.5 coverage of the original words >= floor -> kept; chest: ~0 -> dropped.
    assert [(s.id, s.via) for s in result.symptoms] == [(ids["rash"], "rephrase")]
    step = next(s for s in result.trace if s.key == "rephrase")
    decisions = {row["phrase"]: row["decision"] for row in step.rows}
    assert decisions[f"chest{tag} pain{tag}"] == "dropped"
    assert len(llm.chat_calls) == 1


@db
async def test_rephrase_may_say_the_text_is_outside_the_catalog(
    sessions, catalog, monkeypatch
) -> None:
    """A toothache must not be squeezed into the nearest entry ("headache")."""
    tag, _, llm = catalog
    monkeypatch.setattr(settings, "ai_rephrase_min_best_score", 0.0)
    llm.chat_response = {"variants": []}
    async with sessions() as session:
        result = await ai_symptoms.interpret(session, f"my tooth{tag} hurts")
    assert result.symptoms == []
    step = next(s for s in result.trace if s.key == "rephrase")
    assert "nothing" in step.summary and not step.skipped


@db
async def test_ai_outage_falls_back_to_word_matching(sessions, catalog, monkeypatch) -> None:
    tag, ids, _ = catalog

    def down():
        raise AIUnavailable("gateway down")

    monkeypatch.setattr(ai_symptoms, "get_llm", down)
    async with sessions() as session:
        result = await ai_symptoms.interpret(session, f"I have itchy{tag} spots{tag}")
    assert result.mode == "rule_fallback"
    assert [s.id for s in result.symptoms] == [ids["rash"]]


@db
async def test_recommendation_uses_only_active_rules(sessions, catalog, monkeypatch) -> None:
    _, ids, llm = catalog
    monkeypatch.setattr(ai_symptoms, "redis_client", FakeRedis())
    llm.chat_response = {
        "summary": "s",
        "specialties": [
            {"specialty_id": ids["derm"], "reason": "rash"},
            {"specialty_id": ids["cardio"], "reason": "not in the ranking"},
        ],
    }
    async with sessions() as session:
        result = await ai_symptoms.recommend(session, [ids["rash"]], "itchy spots", explain=True)
    assert [s.specialty_id for s in result.specialties] == [ids["derm"]]
    assert [e.specialty_id for e in result.specialty_explanations] == [ids["derm"]]
    assert result.mode == "ai"

    async with sessions() as session:  # an admin disables the only rule (SCRUM-43)
        await session.execute(
            SymptomSpecialtyRule.__table__.update()
            .where(SymptomSpecialtyRule.symptom_id == ids["rash"])
            .values(is_active=False)
        )
        await session.commit()
        result = await ai_symptoms.recommend(session, [ids["rash"]], None, explain=False)
    assert result.specialties == []
