"""``RuntimeConfig`` (le ``R`` d'ADR-027) et ``Topic`` — les entrées d'une
récupération.

ADR-027 décrit une expérience par le couple **`(W, R)`** :

- **`W`** (normalisation + chunking + embedding) est gravé dans la collection
  Qdrant ; il est *hors périmètre* de l'adapter baseline (B-05) — c'est
  l'orchestrateur de sweep (B-13) qui le fera varier en pilotant l'ingestion.
- **`R`** (runtime) est balayé *par-dessus* une collection déjà produite, sans
  ré-ingestion. C'est ce que modélise ``RuntimeConfig``.

Pour la baseline (config dense de référence), `R` se réduit à deux leviers :
``top_k`` et un seuil de score optionnel. Le modèle est volontairement fermé
(``extra="forbid"`` via ``Frozen``) mais destiné à s'étendre (fusion, rerank,
graphe — ADR-027) sans casser le contrat du port ``Retriever``.

Un ``Topic`` est une requête d'évaluation (le « topic » au sens TREC) : un
identifiant stable et le texte à embarquer. Il ne porte pas de jugement — les
qrels vivent à part (``Judgment``), le contrat d'adapter étant `requête → IDs
ordonnés` (ADR-016), rien de plus.
"""

from __future__ import annotations

from pydantic import Field

from murphy_eval.core.models._base import Frozen


class RuntimeConfig(Frozen):
    """Le ``R`` d'une expérience (ADR-027) : leviers balayés sans ré-ingestion."""

    top_k: int = Field(ge=1)
    """Nombre de chunks demandés à Qdrant par requête (profondeur de la liste)."""
    min_score: float | None = None
    """Seuil de similarité optionnel : les hits sous ce score sont écartés.
    ``None`` = aucun filtrage (on garde les ``top_k`` premiers tels quels)."""


class Topic(Frozen):
    """Une requête d'évaluation : identité stable + texte à embarquer."""

    query_id: str
    text: str
