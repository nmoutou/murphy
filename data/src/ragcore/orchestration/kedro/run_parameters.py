"""Les arbitrages du run : valeurs validées + ``ENVIRONMENT`` → réglages effectifs.

Fonctions pures (sauf ``load_parameters``, qui lit le catalogue). La forme du YAML, elle,
n'est connue que de ``parameters_model`` : les valeurs arrivent ici déjà validées.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from kedro.io import DataCatalog, DatasetError

from ragcore.adapters.config.settings import Environment
from ragcore.core.models.enums import SourceName
from ragcore.orchestration.kedro.parameters_model import DevParameters
from ragcore.sources.registry import all_sources

__all__ = [
    "DEV_ENVIRONMENT",
    "SAFE_DEV_SETTINGS",
    "load_parameters",
    "resolve_dev_settings",
    "resolve_sources",
]

DEV_ENVIRONMENT: Environment = "dev"
"""La seule valeur d'``ENVIRONMENT`` qui applique ``parameters.yml``."""

SAFE_DEV_SETTINGS = DevParameters(
    nuke_all=False,
    embedding_enabled=True,
    skip_unconfigured=True,
    include_path=False,
    include_content_neo4j=False,
)
"""``parameters.yml`` tel qu'il s'applique hors ``dev`` : rien n'est effacé,
l'embedding est calculé, les métadonnées non configurées sont retirées, aucun chemin de
fichier n'est écrit et les nœuds restent maigres."""


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
            "pas de réglages de dev par défaut."
        ) from exc
    return params


def resolve_dev_settings(dev: DevParameters, environment: Environment) -> DevParameters:
    """Les réglages de dev effectifs : le YAML en ``dev``, les valeurs sûres ailleurs.

    L'environnement PRIME, et le défaut penche vers le refus : l'absence
    d'``ENVIRONMENT`` vaut ``prod`` (voir ``InfraSettings.environment``). Chaque clé du
    fichier est une commodité de développement : effacer toutes les bases, couper
    l'embedding (ADR-023), ingérer les métadonnées des balises non configurées,
    écrire les chemins des fichiers source ou hydrater les nœuds Neo4j (ADR-022). Un
    ``parameters.yml`` traîné de dev en prod ne doit pouvoir ni effacer une base, ni
    produire une collection vide, ni écrire dans Mongo ou sur chaque nœud les chemins
    de fichiers du poste d'ingestion. Le signal
    ``tag.unconfigured``, lui, est émis dans les deux régimes.
    """
    return dev if environment == DEV_ENVIRONMENT else SAFE_DEV_SETTINGS


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
