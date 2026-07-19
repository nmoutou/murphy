"""``QdrantSearchClient`` — la recherche des plus proches voisins (lecture seule).

L'ingestion (``ragcore``) est *write-only* sur Qdrant ; le harnais définit son
propre chemin de lecture. Client **synchrone** à dessein : le sweep d'ADR-027 est
séquentiel (une ingestion, une collection, une config à la fois), rien à gagner
à l'asynchrone ici.

Chaque point remonté porte le payload écrit à l'ingestion
(``{chunk_id, identifier, owner_id, **metadata}``) ; on n'en extrait que
``chunk_id`` et ``identifier`` (= ``doc_id`` canonique, ADR-018). Un point sans
ces clés est une incohérence de la collection : on échoue franchement
(fail-fast) plutôt que de fabriquer un run silencieusement faux.
"""

from __future__ import annotations

from collections.abc import Sequence

from qdrant_client import QdrantClient

from murphy_eval.adapters.retrieval.hits import Hit


class QdrantSearchClient:
    """Recherche top-K sur une collection, renvoyant des ``Hit`` triés par score."""

    def __init__(
        self, url: str, collection_name: str, *, api_key: str | None = None
    ) -> None:
        self._client = QdrantClient(url=url, api_key=api_key)
        self._collection_name = collection_name

    def search(self, vector: Sequence[float], *, top_k: int) -> list[Hit]:
        response = self._client.query_points(
            collection_name=self._collection_name,
            query=list(vector),
            limit=top_k,
            with_payload=True,
        )
        return [_point_to_hit(point) for point in response.points]

    def close(self) -> None:
        self._client.close()


def _point_to_hit(point: object) -> Hit:
    payload = getattr(point, "payload", None) or {}
    try:
        chunk_id = payload["chunk_id"]
        identifier = payload["identifier"]
    except KeyError as exc:
        raise ValueError(
            f"Point Qdrant sans clé de payload {exc} — collection incohérente "
            f"avec le contrat d'ingestion (chunk_id + identifier attendus)."
        ) from exc
    score: float = point.score  # type: ignore[attr-defined]  # ScoredPoint, typé object ici
    return Hit(chunk_id=chunk_id, identifier=identifier, score=score)
