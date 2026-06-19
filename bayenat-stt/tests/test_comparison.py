"""Tests for the comparison/selection logic."""

import pytest

from app.engines.base import EngineResult
from app.services import comparison_service


def _result(name: str, text: str, success: bool = True) -> EngineResult:
    return EngineResult(
        engine_name=name,
        language="ar",
        text=text,
        processing_time_seconds=1.0,
        success=success,
        error=None if success else "boom",
    )


def test_identical_texts_full_agreement():
    results = [
        _result("a", "the quick brown fox"),
        _result("b", "the quick brown fox"),
        _result("c", "the quick brown fox"),
    ]
    out = comparison_service.compare(results)
    assert out.agreement_score == 1.0
    assert out.confidence_score == 100.0
    assert out.final_transcript == "the quick brown fox"


def test_majority_consensus_is_chosen_not_outlier():
    # Two engines agree closely; a third is an outlier. The consensus text wins.
    results = [
        _result("a", "the cat sat on the mat"),
        _result("b", "the cat sat on the mat today"),
        _result("c", "completely different nonsense string"),
    ]
    out = comparison_service.compare(results)
    assert out.final_engine in {"a", "b"}
    assert out.final_transcript != "completely different nonsense string"


def test_tie_breaks_toward_longer_text():
    # a and b are mutually identical-ish; tie-break should prefer the longer one.
    results = [
        _result("short", "hello world"),
        _result("long", "hello world friend"),
    ]
    out = comparison_service.compare(results)
    # With two engines, the one more similar to the other (symmetric) ties,
    # so the longer text is selected.
    assert out.final_transcript == "hello world friend"


def test_failed_engines_are_ignored():
    results = [
        _result("ok1", "evidence text here"),
        _result("ok2", "evidence text here"),
        _result("bad", "", success=False),
    ]
    out = comparison_service.compare(results)
    assert out.final_transcript == "evidence text here"
    assert out.agreement_score == 1.0


def test_single_engine_caps_confidence():
    results = [
        _result("only", "single source transcript"),
        _result("bad", "", success=False),
    ]
    out = comparison_service.compare(results)
    assert out.final_transcript == "single source transcript"
    assert out.confidence_score == 50.0


def test_no_usable_engine_raises():
    results = [
        _result("bad1", "", success=False),
        _result("bad2", "   ", success=True),  # whitespace only -> not usable
    ]
    with pytest.raises(ValueError):
        comparison_service.compare(results)


def test_differences_are_reported():
    results = [
        _result("a", "alpha beta gamma"),
        _result("b", "alpha beta delta"),
    ]
    out = comparison_service.compare(results)
    assert len(out.differences) == 1
    diff = out.differences[0]
    assert {"engine_a", "engine_b", "similarity", "length_a", "length_b"} <= set(diff)
