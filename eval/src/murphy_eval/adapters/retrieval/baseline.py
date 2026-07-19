"""``BaselineRetriever`` — la config de récupération de référence (Qdrant dense).

C'est le premier adapter du contrat ADR-016 (`requête → IDs ordonnés`), la
config « baseline » de la DoD v0. Il compose deux collaborateurs derrière des
``Protocol`` (``Embedder`` + ``Searcher``), pour rester testable sans réseau :

    topic.text --Embedder--> vecteur --Searcher--> hits --map--> RunEntry

La seule « intelligence » de l'adapter est le mapping ``hits_to_run_entries``,
extrait en **fonction pure** : c'est là que se joue la couture d'ADR-018 —
``doc_id`` est lu tel quel depuis le payload Qdrant (clé ``identifier``, écrite
par l'ingestion), jamais résolu par un aller-retour Mongo. Le rang est la
position du hit dans l'ordre rendu par Qdrant (1..k), déjà trié par similarité
décroissante.

Le seuil ``min_score`` (``R``) est appliqué **avant** le rang : filtrer d'abord,
numéroter ensuite, pour que les rangs restent contigus (1..n) — invariant que
l'agrégation aval (``aggregate_run``) suppose de toute façon, mais qu'on
respecte dès la source.
"""

from __future__ import annotations

from collections.abc import Sequence

from murphy_eval.adapters.retrieval.hits import Hit
from murphy_eval.core.models.run import Run, RunEntry
from murphy_eval.core.models.runtime import RuntimeConfig, Topic
from murphy_eval.core.ports.retrieval import Embedder, Searcher


def hits_to_run_entries(
    query_id: str,
    hits: Sequence[Hit],
    *,
    min_score: float | None,
    run_tag: str,
) -> list[RunEntry]:
    """Traduit des hits Qdrant ordonnés en ``RunEntry`` pour une requête.

    ``doc_id`` = ``hit.identifier`` (payload d'ingestion, ADR-018), sans
    résolution. Les hits sont supposés déjà triés par similarité décroissante
    (contrat Qdrant) ; le rang est la position 1..n après filtrage ``min_score``.
    """
    kept = [h for h in hits if min_score is None or h.score >= min_score]
    return [
        RunEntry(
            query_id=query_id,
            chunk_id=hit.chunk_id,
            doc_id=hit.identifier,
            rank=rank,
            score=hit.score,
            run_tag=run_tag,
        )
        for rank, hit in enumerate(kept, start=1)
    ]


class BaselineRetriever:
    """Adapter dense de référence — implémente le port ``Retriever`` (ADR-016)."""

    def __init__(
        self, embedder: Embedder, searcher: Searcher, *, run_tag: str = "baseline"
    ) -> None:
        self._embedder = embedder
        self._searcher = searcher
        self._run_tag = run_tag

    def retrieve(self, topics: Sequence[Topic], config: RuntimeConfig) -> Run:
        entries: list[RunEntry] = []
        for topic in topics:
            vector = self._embedder.embed(topic.text)
            hits = self._searcher.search(vector, top_k=config.top_k)
            entries.extend(
                hits_to_run_entries(
                    topic.query_id,
                    hits,
                    min_score=config.min_score,
                    run_tag=self._run_tag,
                )
            )
        return Run(entries=tuple(entries), run_tag=self._run_tag)
