"""Les copies d'une même racine sous une clé, et celle qui fait foi.

L'export DILA garde l'ancienne version d'un texte quand il écrit la nouvelle, parfois
dans l'autre arborescence (``en_vigueur`` / ``non_vigueur``) : rien dans un article ne
date sa version, seule la date de modification du fichier les départage. Sur le stock
LEGI, la copie la plus récente porte toujours l'état le plus avancé
(``ABROGE_DIFF → ABROGE``…).

Des copies identiques se réduisent à une (une collision). Entre copies différentes, la
plus récente reste et chaque autre est écartée (une ``SupersededCopy``) ; à égalité de
date, toutes restent, et le parser refuse le document (``facet_root_duplicated``) plutôt
que de choisir au hasard.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ragcore.core.models.collision_record import CollisionRecord
from ragcore.core.models.enums import SourceName
from ragcore.core.models.problems import CopyStamp, SupersededCopy
from ragcore.core.services.collision_reasons import COLLISION_DUPLICATE_COPY

__all__ = ["Arbitration", "Facet", "arbitrate"]


@dataclass(frozen=True)
class Facet:
    path: str
    tree: dict[str, Any]
    mtime_ns: int


@dataclass(frozen=True)
class Arbitration:
    kept: tuple[Facet, ...]
    """Dans l'ordre des chemins."""
    collisions: tuple[CollisionRecord, ...]
    superseded: tuple[SupersededCopy, ...]


@dataclass(frozen=True)
class _Root:
    source: SourceName
    identifier: str
    tag: str

    def record(
        self, reason: str, kept: Facet, dropped: Sequence[Facet]
    ) -> CollisionRecord:
        """Le fichier retenu en premier, puis les écartés, du plus récent au plus
        ancien."""
        return CollisionRecord(
            source=self.source,
            reason=reason,
            identifier=self.identifier,
            key=self.tag,
            files=(kept.path, *(facet.path for facet in dropped)),
        )

    def superseded(self, kept: Facet, dropped: Sequence[Facet]) -> list[SupersededCopy]:
        return [
            SupersededCopy(
                source=self.source,
                identifier=self.identifier,
                root=self.tag,
                kept=_stamp(kept),
                discarded=_stamp(facet),
            )
            for facet in dropped
        ]


def arbitrate(
    source: SourceName, identifier: str, facets: Sequence[Facet]
) -> Arbitration:
    kept: list[Facet] = []
    collisions: list[CollisionRecord] = []
    superseded: list[SupersededCopy] = []
    for tag, group in _by_root(facets).items():
        root = _Root(source, identifier, tag)
        distinct, merged = _merge_identical(root, group)
        survivors, dropped = _keep_newest(root, distinct)
        kept.extend(survivors)
        collisions.extend(merged)
        superseded.extend(dropped)
    return Arbitration(
        kept=tuple(sorted(kept, key=lambda facet: facet.path)),
        collisions=tuple(collisions),
        superseded=tuple(superseded),
    )


def _by_root(facets: Sequence[Facet]) -> dict[str, list[Facet]]:
    groups: dict[str, list[Facet]] = {}
    for facet in facets:
        groups.setdefault(facet.tree["tag"], []).append(facet)
    return groups


def _merge_identical(
    root: _Root, group: list[Facet]
) -> tuple[list[Facet], list[CollisionRecord]]:
    """Une facette par contenu : la plus récente de ses copies."""
    by_content: list[list[Facet]] = []
    for facet in group:
        same = next((s for s in by_content if s[0].tree == facet.tree), None)
        if same is None:
            by_content.append([facet])
        else:
            same.append(facet)
    distinct: list[Facet] = []
    merged: list[CollisionRecord] = []
    for copies in by_content:
        newest, *older = sorted(copies, key=_newest_first)
        distinct.append(newest)
        if older:
            merged.append(root.record(COLLISION_DUPLICATE_COPY, newest, older))
    return distinct, merged


def _keep_newest(
    root: _Root, distinct: list[Facet]
) -> tuple[list[Facet], list[SupersededCopy]]:
    if len(distinct) == 1:
        return distinct, []
    newest, *older = sorted(distinct, key=_newest_first)
    if older[0].mtime_ns == newest.mtime_ns:
        return distinct, []
    return [newest], root.superseded(newest, older)


def _newest_first(facet: Facet) -> tuple[int, str]:
    return -facet.mtime_ns, facet.path


def _stamp(facet: Facet) -> CopyStamp:
    return CopyStamp(path=facet.path, mtime_ns=facet.mtime_ns)
