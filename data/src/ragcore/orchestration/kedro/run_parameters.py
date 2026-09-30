"""Les paramètres du run : ``parameters.yml`` et ``--params`` → objets typés.

Fonctions pures sur ``params`` (sauf ``load_parameters``, qui lit le catalogue). C'est le
seul endroit du dépôt qui connaisse la forme du YAML ; le hook les appelle en tête de run.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from kedro.io import DataCatalog, DatasetError

from ragcore.adapters.storage.neo4j.node_properties import NodeHydration, NodeLabels
from ragcore.core.models.enums import SourceName
from ragcore.core.models.processing import ChunkingConfig, EmbeddingConfig
from ragcore.sources.registry import all_sources

__all__ = [
    "NukeAllOutsideDevError",
    "load_parameters",
    "resolve_chunking",
    "resolve_embedding_enabled",
    "resolve_embedding_model",
    "resolve_node_hydration",
    "resolve_node_labels",
    "resolve_nuke_all",
    "resolve_skip_unconfigured",
    "resolve_sources",
]


class NukeAllOutsideDevError(RuntimeError):
    """Le mode ``nuke_all`` a été demandé hors d'un environnement `dev`.

    Ce n'est pas un avertissement : c'est un arrêt. Effacer TOUTES les données de
    TOUTES les bases n'a de sens qu'en développement, où les données sont jetables.
    Ailleurs, l'intention est presque sûrement une erreur — et le mode de défaillance
    d'un `nuke` mal placé est irréversible. On lève avant de toucher la moindre base.
    """


def load_parameters(catalog: DataCatalog) -> dict[str, Any]:
    """Charge ``parameters.yml`` depuis le catalogue — ou ARRÊTE le run.

    PAS de fallback silencieux vers ``{}`` : une config illisible n'est pas un run par
    défaut, c'est un run qu'on ARRÊTE, avec une erreur claire (fail-fast, cf. doctrine
    du projet).

    Seule la ``DatasetError`` de Kedro (dont ``DatasetNotFoundError``) est traduite :
    c'est ainsi que le catalogue signale un chargement raté. Toute autre exception est
    un bug, et remonte telle quelle.
    """
    try:
        params: dict[str, Any] = catalog.load("parameters")
    except DatasetError as exc:
        raise RuntimeError(
            "Impossible de charger `parameters.yml` : le run est interrompu. Il n'y a "
            "pas de réglages par défaut pour la découpe ni pour l'embedding."
        ) from exc
    return params


def resolve_chunking(params: dict[str, Any]) -> ChunkingConfig:
    """La découpe (bloc ``chunking``) — ou un ARRÊT si un champ manque ou est mal typé."""
    return ChunkingConfig.model_validate(_require_block(params, "chunking"))


def resolve_embedding_model(params: dict[str, Any]) -> EmbeddingConfig:
    """Le modèle d'embedding et sa dimension (bloc ``embedding``) — ou un ARRÊT."""
    return EmbeddingConfig.model_validate(_require_block(params, "embedding"))


def _require_block(params: dict[str, Any], name: str) -> dict[str, Any]:
    block = params.get(name)
    if not isinstance(block, dict):
        raise ValueError(
            f"Le bloc `{name}` est absent de `parameters.yml` : le run est interrompu."
        )
    return block


def resolve_embedding_enabled(params: dict[str, Any], environment: str) -> bool:
    """L'embedding est-il calculé pour ce run ? (ADR-023)

    Deux entrées, et l'environnement PRIME. Le flag YAML ``embedding_runtime.enabled``
    (obligatoire, validé dans tous les environnements) n'a d'effet qu'en ``dev`` ; partout ailleurs
    on embarque toujours. C'est la même asymétrie que ``nuke_all`` : couper l'embedding
    est une commodité de développement, et une commodité ne doit jamais pouvoir dégrader
    la prod par simple oubli d'une variable. Un ``parameters.yml`` traîné de dev en prod
    avec ``enabled: false`` produirait sinon une collection vide sans que rien ne lève.

    Le flag vit sous ``embedding_runtime``, à part du bloc ``embedding`` qui porte le
    modèle et sa dimension.
    """
    is_enabled = _require_bool(params, "embedding_runtime.enabled")
    return is_enabled or environment != "dev"


def resolve_node_hydration(params: dict[str, Any], environment: str) -> NodeHydration:
    """L'hydratation des nœuds Neo4j — arbitrée par l'environnement (ADR-022 §2).

    Hors ``dev``, le nœud est MAIGRE et les toggles YAML sont ignorés — garde-fou dur,
    même asymétrie que ``nuke_all`` et l'interrupteur d'embedding : un
    ``include_path: true`` traîné en prod écrirait les chemins de fichiers du poste
    d'ingestion sur chaque nœud, une info locale sans valeur ailleurs que sur ce poste.

    Les deux toggles sont obligatoires et validés dans tous les environnements. En dev,
    le YAML ouvre ou referme chaque vanne : ``include_path`` = chemins des FICHIERS source,
    ``include_content`` = texte du document (``_text_content``). Ces toggles ne
    concernent QUE Neo4j — le format de clé des métadonnées, lui, n'est pas un toggle.
    """
    include_path = _require_bool(params, "exportation.neo4j.include_path")
    include_content = _require_bool(params, "exportation.neo4j.include_content")
    if environment != "dev":
        return NodeHydration()
    return NodeHydration(
        metadata=True, include_path=include_path, include_content=include_content
    )


def resolve_node_labels(params: dict[str, Any]) -> NodeLabels:
    """Les labels des nœuds Neo4j, d'après le préfixe de l'identifiant — ou un ARRÊT.

    PAS de table par défaut dans le code : ``exportation.neo4j.labels`` est la seule
    source. Un bloc absent arrête le run, plutôt que d'écrire tout le graphe sous un
    label que personne n'a choisi. Contrairement à l'hydratation, l'environnement
    n'arbitre rien ici : le label d'un nœud est le même en dev et en prod.
    """
    labels = params.get("exportation", {}).get("neo4j", {}).get("labels")
    if not isinstance(labels, dict) or not labels.get("default"):
        raise ValueError(
            "`exportation.neo4j.labels` est absent de `parameters.yml`, ou n'a pas de "
            "`default` : le run est interrompu. Attendu : un label `default` et une "
            "table `by_prefix` (p. ex. `LEGIARTI: Article`)."
        )
    by_prefix = labels.get("by_prefix") or {}
    return NodeLabels(
        default=str(labels["default"]),
        by_prefix={str(prefix): str(label) for prefix, label in by_prefix.items()},
    )


def resolve_skip_unconfigured(params: dict[str, Any], environment: str) -> bool:
    """Les métadonnées des balises non configurées sont-elles retirées ? (ADR-022 §1)

    Le flag YAML ``exportation.skip_unconfigured`` (obligatoire, validé dans tous les
    environnements) n'a d'effet qu'en ``dev`` ; partout ailleurs on retire toujours.
    Même asymétrie que l'embedding : ingérer les balises non configurées est une
    commodité d'itération sur le modèle de données, et un ``false`` traîné de dev en
    prod ne doit pas remplir la prod de métadonnées que personne n'a choisies. Le
    signal ``tag.unconfigured``, lui, est émis dans les deux régimes.
    """
    is_skipped = _require_bool(params, "exportation.skip_unconfigured")
    return is_skipped or environment != "dev"


def resolve_nuke_all(params: dict[str, Any], environment: str) -> bool:
    """L'effacement de toutes les bases en tête de run — refusé hors ``dev``.

    Le refus a lieu ici, dans le plan du run : avant tout nœud, avant qu'aucun client
    ne soit ouvert. L'absence de ``ENVIRONMENT`` vaut ``prod`` (voir
    ``InfraSettings.environment``) : un ``.env`` incomplet est traité comme protégé.
    """
    is_requested = _require_bool(params, "maintenance.nuke_all")
    if is_requested and environment != "dev":
        raise NukeAllOutsideDevError(
            f"nuke_all refusé : ENVIRONMENT={environment!r}, attendu 'dev'. "
            "Ce mode efface TOUTES les données de TOUTES les bases — il n'est autorisé "
            "que là où les données sont jetables. Pour l'exécuter, ENVIRONMENT doit "
            "valoir strictement 'dev' dans le .env de la racine."
        )
    return is_requested


def _require_bool(params: dict[str, Any], path: str) -> bool:
    """La valeur booléenne au chemin pointé ``path`` — ou un ARRÊT.

    Pas de ``bool(...)`` : la chaîne ``"false"`` vaudrait vrai. Pas de défaut non plus :
    une clé absente ou mal typée arrête le run, avant qu'un nœud ne touche aux bases.
    """
    value: object = params
    for key in path.split("."):
        value = value.get(key) if isinstance(value, dict) else None
    if not isinstance(value, bool):
        raise ValueError(
            f"`{path}` est absent de `parameters.yml` ou n'est pas un booléen "
            f"(reçu : {value!r}) : le run est interrompu. Attendu : `true` ou `false`."
        )
    return value


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
