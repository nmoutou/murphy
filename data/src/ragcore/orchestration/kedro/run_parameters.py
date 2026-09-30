"""Les arbitrages du run : valeurs validées + ``ENVIRONMENT`` → réglages effectifs.

Fonctions pures (sauf ``load_parameters``, qui lit le catalogue). La forme du YAML, elle,
n'est connue que de ``parameters_model`` : les valeurs arrivent ici déjà validées.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from kedro.io import DataCatalog, DatasetError

from ragcore.adapters.storage.neo4j.node_properties import NodeHydration
from ragcore.core.models.enums import SourceName
from ragcore.orchestration.kedro.parameters_model import Neo4jParameters
from ragcore.sources.registry import all_sources

__all__ = [
    "NukeAllOutsideDevError",
    "load_parameters",
    "resolve_embedding_enabled",
    "resolve_node_hydration",
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


def resolve_embedding_enabled(is_enabled: bool, environment: str) -> bool:
    """L'embedding est-il calculé pour ce run ? (ADR-023)

    Deux entrées, et l'environnement PRIME. Le flag YAML ``embedding_runtime.enabled``
    (déjà validé par ``parameters_model``) n'a d'effet qu'en ``dev`` ; partout ailleurs
    on embarque toujours. C'est la même asymétrie que ``nuke_all`` : couper l'embedding
    est une commodité de développement, et une commodité ne doit jamais pouvoir dégrader
    la prod par simple oubli d'une variable. Un ``parameters.yml`` traîné de dev en prod
    avec ``enabled: false`` produirait sinon une collection vide sans que rien ne lève.
    """
    return is_enabled or environment != "dev"


def resolve_node_hydration(neo4j: Neo4jParameters, environment: str) -> NodeHydration:
    """L'hydratation des nœuds Neo4j — arbitrée par l'environnement (ADR-022 §2).

    Hors ``dev``, le nœud est MAIGRE et les toggles YAML sont ignorés — garde-fou dur,
    même asymétrie que ``nuke_all`` et l'interrupteur d'embedding : un
    ``include_path: true`` traîné en prod écrirait les chemins de fichiers du poste
    d'ingestion sur chaque nœud, une info locale sans valeur ailleurs que sur ce poste.

    En dev, le YAML ouvre ou referme chaque vanne : ``include_path`` = chemins des
    FICHIERS source, ``include_content`` = texte du document (``_text_content``). Ces
    toggles ne concernent QUE Neo4j — le format de clé des métadonnées, lui, n'est pas
    un toggle.
    """
    if environment != "dev":
        return NodeHydration()
    return NodeHydration(
        metadata=True,
        include_path=neo4j.include_path,
        include_content=neo4j.include_content,
    )


def resolve_skip_unconfigured(is_skipped: bool, environment: str) -> bool:
    """Les métadonnées des balises non configurées sont-elles retirées ? (ADR-022 §1)

    Le flag YAML ``exportation.skip_unconfigured`` (déjà validé par
    ``parameters_model``) n'a d'effet qu'en ``dev`` ; partout ailleurs on retire
    toujours. Même asymétrie que l'embedding : ingérer les balises non configurées est
    une commodité d'itération sur le modèle de données, et un ``false`` traîné de dev en
    prod ne doit pas remplir la prod de métadonnées que personne n'a choisies. Le
    signal ``tag.unconfigured``, lui, est émis dans les deux régimes.
    """
    return is_skipped or environment != "dev"


def resolve_nuke_all(is_requested: bool, environment: str) -> bool:
    """L'effacement de toutes les bases en tête de run — refusé hors ``dev``.

    Le refus a lieu ici, dans le plan du run : avant tout nœud, avant qu'aucun client
    ne soit ouvert. L'absence de ``ENVIRONMENT`` vaut ``prod`` (voir
    ``InfraSettings.environment``) : un ``.env`` incomplet est traité comme protégé.
    """
    if is_requested and environment != "dev":
        raise NukeAllOutsideDevError(
            f"nuke_all refusé : ENVIRONMENT={environment!r}, attendu 'dev'. "
            "Ce mode efface TOUTES les données de TOUTES les bases — il n'est autorisé "
            "que là où les données sont jetables. Pour l'exécuter, ENVIRONMENT doit "
            "valoir strictement 'dev' dans le .env de la racine."
        )
    return is_requested


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
