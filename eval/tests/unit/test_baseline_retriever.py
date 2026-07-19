from __future__ import annotations

from collections.abc import Sequence

from murphy_eval.adapters.retrieval.baseline import BaselineRetriever
from murphy_eval.adapters.retrieval.hits import Hit
from murphy_eval.core.models.runtime import RuntimeConfig, Topic
from murphy_eval.core.ports.retriever import Retriever


class _FakeEmbedder:
    """Embarque en renvoyant un vecteur trivial ; enregistre les textes vus."""

    def __init__(self) -> None:
        self.seen: list[str] = []

    def embed(self, text: str) -> Sequence[float]:
        self.seen.append(text)
        return [0.0, 1.0]


class _FakeSearcher:
    """Renvoie des hits pré-programmés par requête, dans l'ordre donné."""

    def __init__(self, hits_by_call: list[list[Hit]]) -> None:
        self._hits_by_call = hits_by_call
        self.top_ks: list[int] = []

    def search(self, vector: Sequence[float], *, top_k: int) -> list[Hit]:
        self.top_ks.append(top_k)
        return self._hits_by_call.pop(0)


def test_baseline_retriever_satisfait_le_port() -> None:
    """Discipline des ports : l'adapter concret est bien un ``Retriever``."""
    retriever: Retriever = BaselineRetriever(_FakeEmbedder(), _FakeSearcher([]))
    assert retriever is not None


def test_produit_un_run_concatene_sur_toutes_les_requetes() -> None:
    embedder = _FakeEmbedder()
    searcher = _FakeSearcher(
        [
            [Hit(chunk_id="c1", identifier="eli:D1", score=0.9)],
            [Hit(chunk_id="c2", identifier="decision:D2", score=0.8)],
        ]
    )
    retriever = BaselineRetriever(embedder, searcher, run_tag="baseline")

    run = retriever.retrieve(
        [Topic(query_id="q1", text="texte 1"), Topic(query_id="q2", text="texte 2")],
        RuntimeConfig(top_k=5),
    )

    assert embedder.seen == ["texte 1", "texte 2"]
    assert searcher.top_ks == [5, 5]
    assert [(e.query_id, e.doc_id, e.rank) for e in run.entries] == [
        ("q1", "eli:D1", 1),
        ("q2", "decision:D2", 1),
    ]
    assert run.run_tag == "baseline"


def test_min_score_de_la_config_filtre_les_hits() -> None:
    searcher = _FakeSearcher(
        [
            [
                Hit(chunk_id="c1", identifier="eli:D1", score=0.9),
                Hit(chunk_id="c2", identifier="eli:D2", score=0.3),
            ]
        ]
    )
    retriever = BaselineRetriever(_FakeEmbedder(), searcher)

    run = retriever.retrieve(
        [Topic(query_id="q1", text="t")], RuntimeConfig(top_k=5, min_score=0.5)
    )

    assert [e.chunk_id for e in run.entries] == ["c1"]
