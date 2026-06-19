"""Compare transcripts from multiple engines and choose the final text.

Selection logic (per the product spec):

1. Consider **only successful** engine outputs.
2. Compute pairwise similarity (Levenshtein ratio) between every pair.
3. ``agreement_score`` = mean of all pairwise similarities (0..1).
4. Final text = the transcript with the **highest mean similarity** to the
   others. Ties break toward the **longer / more complete** text — the system
   deliberately does *not* pick "longest" outright.
5. ``confidence_score`` = agreement expressed as a percentage (0..100), scaled
   down when fewer engines corroborate the result.
6. A ``differences`` list summarises pairwise divergence (WER + length deltas).

``python-Levenshtein`` and ``jiwer`` are imported lazily with pure-Python
fallbacks so the comparison still works (and tests still run) if they are absent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.engines.base import EngineResult

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    final_transcript: str
    final_engine: Optional[str]
    agreement_score: float  # 0..1
    confidence_score: float  # 0..100
    differences: List[dict] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Similarity primitives (with graceful fallbacks)
# --------------------------------------------------------------------------- #
def _levenshtein_ratio(a: str, b: str) -> float:
    """Similarity in [0, 1]; 1.0 means identical."""
    if a == b:
        return 1.0
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    try:
        import Levenshtein  # type: ignore

        return float(Levenshtein.ratio(a, b))
    except Exception:  # noqa: BLE001 - fallback to stdlib difflib
        from difflib import SequenceMatcher

        return SequenceMatcher(None, a, b).ratio()


def _word_error_rate(reference: str, hypothesis: str) -> Optional[float]:
    """Word error rate between two transcripts, or ``None`` if it cannot be computed."""
    if not reference and not hypothesis:
        return 0.0
    try:
        import jiwer  # type: ignore

        return float(jiwer.wer(reference or " ", hypothesis or " "))
    except Exception:  # noqa: BLE001
        return None


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def compare(results: List[EngineResult]) -> ComparisonResult:
    """Compare engine results and select the final transcript.

    Raises :class:`ValueError` if no engine produced usable text.
    """
    successful = [r for r in results if r.success and r.text.strip()]

    if not successful:
        raise ValueError("No engine produced a usable transcript.")

    if len(successful) == 1:
        only = successful[0]
        logger.info("Only one successful engine (%s); confidence is capped.", only.engine_name)
        return ComparisonResult(
            final_transcript=only.text,
            final_engine=only.engine_name,
            agreement_score=1.0,
            # A single source cannot be corroborated; cap confidence.
            confidence_score=50.0,
            differences=[],
        )

    texts = [r.text for r in successful]
    n = len(successful)

    # Pairwise similarity matrix and the list of all pairwise scores.
    sim = [[1.0] * n for _ in range(n)]
    pairwise_scores: List[float] = []
    differences: List[dict] = []
    for i in range(n):
        for j in range(i + 1, n):
            ratio = _levenshtein_ratio(texts[i], texts[j])
            sim[i][j] = sim[j][i] = ratio
            pairwise_scores.append(ratio)
            differences.append(
                {
                    "engine_a": successful[i].engine_name,
                    "engine_b": successful[j].engine_name,
                    "similarity": round(ratio, 4),
                    "word_error_rate": _round_opt(_word_error_rate(texts[i], texts[j])),
                    "length_a": len(texts[i]),
                    "length_b": len(texts[j]),
                }
            )

    agreement_score = _mean(pairwise_scores)

    # Mean similarity of each text to the others.
    mean_to_others = [
        _mean([sim[i][j] for j in range(n) if j != i]) for i in range(n)
    ]

    # Pick highest mean similarity; tie-break on longer (more complete) text.
    best_index = 0
    best_score = (-1.0, -1)
    for i in range(n):
        score = (round(mean_to_others[i], 6), len(texts[i]))
        if score > best_score:
            best_score = score
            best_index = i

    final = successful[best_index]
    confidence_score = _confidence_from_agreement(agreement_score, n)

    logger.info(
        "Selected %s as final transcript (agreement=%.3f, confidence=%.1f)",
        final.engine_name,
        agreement_score,
        confidence_score,
    )
    return ComparisonResult(
        final_transcript=final.text,
        final_engine=final.engine_name,
        agreement_score=round(agreement_score, 4),
        confidence_score=round(confidence_score, 2),
        differences=differences,
    )


def _confidence_from_agreement(agreement: float, engine_count: int) -> float:
    """Map agreement (0..1) to a confidence percentage (0..100).

    More corroborating engines raise the ceiling: two agreeing engines are good,
    three are better. The factor is 0.9 for 2 engines and reaches 1.0 at 3+, so
    perfect agreement across three engines yields full confidence.
    """
    corroboration_factor = min(1.0, 0.9 + 0.1 * (engine_count - 2))
    return max(0.0, min(100.0, agreement * 100.0 * corroboration_factor))


def _round_opt(value: Optional[float]) -> Optional[float]:
    return round(value, 4) if value is not None else None
