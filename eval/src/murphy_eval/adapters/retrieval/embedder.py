"""``TeiEmbedder`` — embarque du texte via le service TEI (OpenAI-compatible).

Réplique le contrat de l'ingestion (``ragcore/adapters/embedding/openai_embedder``)
sans l'importer (ADR-027) : ``POST {base_url}/embeddings``, corps
``{"model": <id>, "input": [textes]}``, réponse ``{"data": [{"index","embedding"}]}``.

Deux garde-fous, tirés du même contrat :

- **Tri par ``index``** : TEI ne garantit pas l'ordre de ``data`` ; on réordonne.
- **Le modèle est passé verbatim** (``sentence-transformers/all-mpnet-base-v2``) :
  c'est la chaîne exacte hashée dans le nom de collection et servie par TEI.
  L'embarquer avec un autre modèle produirait des vecteurs incomparables à ceux
  de la collection — d'où la dimension attendue vérifiée à la réponse.
"""

from __future__ import annotations

from collections.abc import Sequence

import httpx


class TeiEmbedder:
    """Client d'embedding TEI, un texte à la fois (le harnais embarque par requête).

    Volontairement mono-texte : la baseline embarque une requête à la fois. L'API
    accepte pourtant un batch (``input`` est déjà une liste) — un ``embed_many``
    serait un gain net quand le sweep B-13 évaluera beaucoup de topics ; reporté
    tant que le volume ne le justifie pas.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        api_key: str | None = None,
        dimension: int = 768,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dimension = dimension
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
        self._timeout = timeout

    def embed(self, text: str) -> Sequence[float]:
        response = httpx.post(
            f"{self._base_url}/embeddings",
            json={"model": self._model, "input": [text]},
            headers=self._headers,
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()["data"]
        ordered = sorted(data, key=lambda item: item["index"])
        embedding: list[float] = [float(x) for x in ordered[0]["embedding"]]
        if len(embedding) != self._dimension:
            raise ValueError(
                f"Dimension d'embedding inattendue : {len(embedding)} "
                f"(attendu {self._dimension} pour {self._model})"
            )
        return embedding
