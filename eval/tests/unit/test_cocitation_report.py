from __future__ import annotations

from murphy_eval.core.models.cocitation import CocitationPair
from murphy_eval.core.services.cocitation_report import summarize_pairs


def _pair(source: str, verb: str, target: str) -> CocitationPair:
    return CocitationPair(source=source, verb=verb, target=target)


def test_summarize_compte_paires_documents_et_verbes() -> None:
    pairs = [
        _pair("a", "cites", "b"),
        _pair("a", "cites", "c"),
        _pair("b", "succeeded_by", "d"),
    ]
    summary = summarize_pairs(pairs)
    assert summary.pair_count == 3
    # a, b, c, d = 4 documents distincts
    assert summary.document_count == 4
    # trié par verbe
    assert summary.pairs_by_verb == (("cites", 2), ("succeeded_by", 1))


def test_summarize_jeu_vide() -> None:
    summary = summarize_pairs([])
    assert summary.pair_count == 0
    assert summary.document_count == 0
    assert summary.pairs_by_verb == ()


def test_document_compte_source_et_cible_sans_double_comptage() -> None:
    # 'a' apparaît en source ET en cible : compté une seule fois.
    pairs = [_pair("a", "cites", "b"), _pair("b", "cites", "a")]
    summary = summarize_pairs(pairs)
    assert summary.document_count == 2
