"""Le registre des sources : une source est une ligne de données, pas une classe ni
une branche d'``if``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ragcore.core.models.enums import SourceName
from ragcore.sources.generic import RoleTable
from ragcore.sources.jurisprudence import (
    JURI_ADMIN_ROLE_TABLE,
    JURI_CONSTIT_ROLE_TABLE,
    JURI_JUDI_ROLE_TABLE,
    JuriFileConnector,
)
from ragcore.sources.legislatif.file_connector import LegiFileConnector
from ragcore.sources.legislatif.table import LEGI_ROLE_TABLE

__all__ = ["SOURCES", "SourceDefinition", "definition_for"]


@dataclass(frozen=True)
class SourceDefinition:
    """Tout ce que ragcore doit savoir d'une source."""

    connector: Callable[[Path], Any]
    """Une fabrique : le chemin racine n'est connu qu'à l'exécution."""

    table: RoleTable
    subdirectory: str
    """Sous la racine du corpus (``xml_source_path``) : un fait sur la source, pas de la
    configuration."""


SOURCES: Mapping[SourceName, SourceDefinition] = {
    SourceName.LEGI: SourceDefinition(
        connector=lambda root: LegiFileConnector(root),
        table=LEGI_ROLE_TABLE,
        subdirectory="LEGI",
    ),
    # ── Les cinq sources de jurisprudence ──────────────────────────────────────
    #
    # CAPP, CASS et INCA partagent la même table : même racine, `TEXTE_JURI_JUDI`.
    SourceName.CAPP: SourceDefinition(
        connector=lambda root: JuriFileConnector(root, SourceName.CAPP),
        table=JURI_JUDI_ROLE_TABLE,
        subdirectory="CAPP",
    ),
    SourceName.CASS: SourceDefinition(
        connector=lambda root: JuriFileConnector(root, SourceName.CASS),
        table=JURI_JUDI_ROLE_TABLE,
        subdirectory="CASS",
    ),
    SourceName.INCA: SourceDefinition(
        connector=lambda root: JuriFileConnector(root, SourceName.INCA),
        table=JURI_JUDI_ROLE_TABLE,
        subdirectory="INCA",
    ),
    SourceName.JADE: SourceDefinition(
        connector=lambda root: JuriFileConnector(root, SourceName.JADE),
        table=JURI_ADMIN_ROLE_TABLE,
        subdirectory="JADE",
    ),
    SourceName.CONSTIT: SourceDefinition(
        connector=lambda root: JuriFileConnector(root, SourceName.CONSTIT),
        table=JURI_CONSTIT_ROLE_TABLE,
        subdirectory="CONSTIT",
    ),
}
"""Les sources ingérables. ``JORF`` et ``UPLOAD`` n'y sont pas : leur connecteur n'est
pas écrit, et les demander lève au démarrage.
"""


def definition_for(source: SourceName) -> SourceDefinition:
    """Lève en nommant les sources disponibles si elle n'est pas connue."""
    definition = SOURCES.get(source)
    if definition is None:
        connues = ", ".join(sorted(s.value for s in SOURCES))
        msg = (
            f"Source non ingérable : {source.value!r}. "
            f"Aucun connecteur ni table ne lui est associé. Sources connues : {connues}."
        )
        raise ValueError(msg)
    return definition


def all_sources() -> tuple[SourceName, ...]:
    """Ce qu'un ``kedro run`` nu traite. ``SOURCES`` fait foi, pas ``SourceName`` : l'enum
    contient des sources sans connecteur. Ordre stable, pour un run reproductible.
    """
    return tuple(SOURCES)
