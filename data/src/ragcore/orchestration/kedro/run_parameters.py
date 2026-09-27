"""Les paramètres du run : ``parameters.yml`` et ``--params`` → objets typés.

Fonctions pures sur ``params`` (sauf ``load_parameters``, qui lit le catalogue). C'est le
seul endroit du dépôt qui connaisse la forme du YAML ; le hook les appelle en tête de run.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from kedro.io import DataCatalog, DatasetError

from ragcore.adapters.storage.neo4j.graph_repository import NodeHydration
from ragcore.core.config import (
    ChunkingConfig,
    EmbeddingConfig,
    NormalizationConfig,
    WorkflowConfig,
)
from ragcore.core.models.enums import SourceName
from ragcore.sources.registry import all_sources

__all__ = [
    "build_workflow_config",
    "load_parameters",
    "resolve_embedding_enabled",
    "resolve_node_hydration",
    "resolve_sources",
]


def load_parameters(catalog: DataCatalog) -> dict[str, Any]:
    """Charge ``parameters.yml`` depuis le catalogue — ou ARRÊTE le run.

    PAS de fallback silencieux vers ``{}`` : ``build_workflow_config({})`` produirait la
    config par DÉFAUT (chunk_size=128…), donc un ``collection_name`` par défaut — et le
    run écrirait tout le corpus dans une collection nommée d'après une stratégie que
    l'utilisateur n'a pas choisie, en écrasant potentiellement l'A/B d'un autre run. Une
    config illisible n'est pas un run par défaut : c'est un run qu'on ARRÊTE, avec une
    erreur claire (fail-fast, cf. doctrine du projet).

    Seule la ``DatasetError`` de Kedro (dont ``DatasetNotFoundError``) est traduite :
    c'est ainsi que le catalogue signale un chargement raté. Toute autre exception est
    un bug, et remonte telle quelle.
    """
    try:
        params: dict[str, Any] = catalog.load("parameters")
    except DatasetError as exc:
        raise RuntimeError(
            "Impossible de charger `parameters.yml` : le run est interrompu. "
            "Continuer avec les défauts baptiserait la collection Qdrant d'après "
            "une config que personne n'a choisie — une perte silencieuse de la "
            "stratégie d'ingestion."
        ) from exc
    return params


def build_workflow_config(params: dict[str, Any]) -> WorkflowConfig:
    """``parameters.yml`` → ``WorkflowConfig``. La seule traduction, et elle est ici.

    C'est le point où Kedro cesse d'être la vérité (§9) : le YAML *peuple* la config,
    il ne la *définit* pas. Cette fonction est le seul endroit du dépôt qui connaisse la
    forme du YAML ; ``core/`` n'en sait rien et ne doit rien en savoir.

    Les défauts ne sont pas des valeurs de confort : chacun est une décision qui sera
    hashée. Un défaut qui change en silence change le nom de la collection, donc écrit
    les vecteurs ailleurs — d'où le cliquet ``golden/test_fingerprint.py``.
    """
    workflow = params.get("workflow", {})
    chunking = workflow.get("chunking", {})
    normalization = workflow.get("normalization", {})
    embedding = workflow.get("embedding", {})

    return WorkflowConfig(
        normalization=NormalizationConfig(
            # §4 n'est pas écrite : il n'y a aujourd'hui AUCUNE normalisation
            # typographique. « none » le dit. Le jour où elle atterrit, elle exporte sa
            # version, ce champ la lit, et la collection change toute seule.
            version=normalization.get("version", "none"),
        ),
        chunking=ChunkingConfig(
            strategy=chunking.get("strategy", "legi-structural-v1"),
            size=chunking.get("chunk_size", 128),
            overlap=chunking.get("chunk_overlap", 25),
        ),
        embedding=EmbeddingConfig(
            model_name=embedding.get(
                "embedding_model", "sentence-transformers/all-mpnet-base-v2"
            ),
            dimension=embedding.get("dimension", 768),
        ),
    )


def resolve_embedding_enabled(params: dict[str, Any], environment: str) -> bool:
    """L'embedding est-il calculé pour ce run ? (ADR-023)

    Deux entrées, et l'environnement PRIME. Le flag YAML ``embedding.enabled`` (défaut
    ``true`` : le comportement historique) n'a d'effet qu'en ``dev`` ; partout ailleurs
    on embarque toujours. C'est la même asymétrie que ``nuke_all`` : couper l'embedding
    est une commodité de développement, et une commodité ne doit jamais pouvoir dégrader
    la prod par simple oubli d'une variable. Un ``parameters.yml`` traîné de dev en prod
    avec ``enabled: false`` produirait sinon une collection vide sans que rien ne lève.

    Le flag vit sous ``embedding_runtime`` (ADR-026 : séparé du bloc ``workflow.embedding``
    qui porte modèle et dimension) et n'entre PAS dans le ``WorkflowConfig`` ni dans le
    hash (§6) : ne pas produire de vecteurs n'invalide aucun vecteur —
    ``build_workflow_config`` l'ignore, et c'est voulu.
    """
    if environment != "dev":
        return True
    embedding_runtime = params.get("embedding_runtime", {})
    return bool(embedding_runtime.get("enabled", True))


def resolve_node_hydration(params: dict[str, Any], environment: str) -> NodeHydration:
    """L'hydratation des nœuds Neo4j — arbitrée par l'environnement (ADR-022 §2).

    Hors ``dev``, le nœud est MAIGRE et les toggles YAML sont ignorés — garde-fou dur,
    même asymétrie que ``nuke_all`` et l'interrupteur d'embedding : un
    ``include_path: true`` traîné en prod écrirait les chemins de fichiers du poste
    d'ingestion sur chaque nœud, une info locale sans valeur ailleurs que sur ce poste.

    En dev, tout est ouvert par défaut (Neo4j est l'outil d'inspection de la v0) et le
    YAML peut refermer chaque vanne : ``include_path`` = chemins des FICHIERS source,
    ``include_content`` = texte du document (``_text_content``). Ces toggles ne
    concernent QUE Neo4j — le format de clé des métadonnées, lui, n'est pas un toggle.
    """
    if environment != "dev":
        return NodeHydration()
    neo4j = params.get("exportation", {}).get("neo4j", {})
    return NodeHydration(
        metadata=True,
        include_path=bool(neo4j.get("include_path", True)),
        include_content=bool(neo4j.get("include_content", True)),
    )


def resolve_sources(
    value: str | SourceName | Iterable[str] | None,
) -> tuple[SourceName, ...]:
    """Les sources demandées, ou une erreur qui dit quoi faire.

    Accepte ce qu'un opérateur écrit réellement en ligne de commande :

    - rien / ``"all"``       → **toutes** les sources ingérables (le défaut)
    - ``"cass"``             → une seule
    - ``"cass,jade"``        → plusieurs (Kedro passe les ``--params`` en chaîne)
    - une liste YAML         → plusieurs, si le paramètre vient d'un fichier de conf

    Un ``--params source=cas`` (faute de frappe) doit échouer **au démarrage**, en nommant
    les sources valides. Sans ça, Kedro partirait sur une source inconnue et le run
    n'ingérerait rien — un échec silencieux qui ressemble à un corpus vide. C'est la même
    raison qui fait qu'on ne *filtre* pas les inconnues d'une liste : ``cass,jade`` avec
    une coquille sur ``jade`` doit se plaindre, pas ingérer CASS en silence.
    """
    if value is None:
        return all_sources()

    if isinstance(value, SourceName):
        return (value,)

    if isinstance(value, str):
        # « all » est le nom explicite du défaut. Il existe pour qu'un `.env` ou un
        # `--params` puisse *demander* le comportement par défaut, plutôt que de devoir
        # énumérer six sources pour dire « toutes ».
        if value.strip().lower() in {"", "all", "*"}:
            return all_sources()
        names: list[str] = [part.strip() for part in value.split(",") if part.strip()]
    else:
        names = [str(part).strip() for part in value]

    if not names:
        return all_sources()

    resolved: list[SourceName] = []
    for name in names:
        try:
            source = SourceName(name.lower())
        except ValueError as exc:
            connues = ", ".join(s.value for s in all_sources())
            msg = f"Source inconnue : {name!r}. Sources ingérables : {connues}."
            raise ValueError(msg) from exc
        if source not in resolved:
            resolved.append(source)

    return tuple(resolved)
