"""Les valeurs d'une clé de métadonnée, toutes gardées, puis résolues (ADR-049).

``collect_metadata`` et la cascade des balises non configurées ne tranchent plus : elles
AJOUTENT chaque occurrence à sa clé, dans l'ordre où elles lisent le document — facettes
dans l'ordre de ``RoleTable.roots``, puis ordre du document. Ce module tranche, une fois :

- des valeurs identiques sont dédoublonnées, et ne font pas de collision ;
- une clé ``list`` est TOUJOURS une liste, même avec une seule valeur ;
- deux valeurs distinctes font une collision : la clé devient une liste, sauf une clé
  renommée hors ``list_keys``, qui BLOQUE le document. La table ne dit pas laquelle
  garder, et choisir en silence est exactement ce que cet ADR supprime.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ragcore.core.models.collision import Collision, CollisionValue
from ragcore.core.models.enums import SourceName

from .role_table import RoleTable

__all__ = ["Occurrence", "Resolution", "resolve"]


@dataclass(frozen=True)
class Occurrence:
    """Une valeur lue, et d'où elle vient."""

    value: str
    source_file: str


@dataclass(frozen=True)
class Resolution:
    """Les métadonnées du document, ses collisions, et les clés qui le bloquent."""

    metadata: dict[str, Any]
    collisions: tuple[Collision, ...]
    blocking: tuple[str, ...]


def resolve(
    occurrences: Mapping[str, Sequence[Occurrence]],
    table: RoleTable,
    source: SourceName,
    identifier: str,
) -> Resolution:
    """Résout chaque clé en valeur ou en liste, et relève ses collisions."""
    renamed = set(table.meta_renames.values())
    metadata: dict[str, Any] = {}
    collisions: list[Collision] = []
    blocking: list[str] = []
    for key, found in occurrences.items():
        distinct = list(dict.fromkeys(occurrence.value for occurrence in found))
        is_list = key in table.list_keys
        metadata[key] = distinct if is_list or len(distinct) > 1 else distinct[0]
        if len(distinct) == 1:
            continue
        collisions.append(_collision(source, identifier, key, found))
        if key in renamed and not is_list:
            blocking.append(key)
    return Resolution(metadata, tuple(collisions), tuple(blocking))


def _collision(
    source: SourceName, identifier: str, key: str, found: Sequence[Occurrence]
) -> Collision:
    return Collision(
        source=source,
        identifier=identifier,
        key=key,
        values=tuple(
            CollisionValue(value=occurrence.value, source_file=occurrence.source_file)
            for occurrence in found
        ),
    )
