"""Les cibles décrites : un lien sans ``@id`` devient une ``UnformattedRelation``."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..models.unformatted_relation import UnformattedRelation
from .subject import LinkSubject
from .table import LinkTable
from .vocabulary import translate

__all__ = ["unformatted_relation_from"]


def unformatted_relation_from(
    reference: Mapping[str, Any],
    table: LinkTable,
    subject: LinkSubject,
) -> UnformattedRelation | None:
    """Appelée quand l'``@id`` est vide, quelle que soit la source.

    ``None`` sans texte de désignation : la balise ne dit alors rien du tout. Le verbe
    est traduit si la table le sait, brut sinon.
    """
    target_text = str(reference.get("label", "")).strip()
    if not target_text:
        return None

    raw_typelien = str(reference.get("typelien", ""))
    verb, _ = translate(table.translation, raw_typelien)
    return UnformattedRelation(
        source_identifier=subject.current,
        target_text=target_text,
        relation_type=str(verb) if verb is not None else raw_typelien,
        sens=str(reference.get("sens", "")),
        source=subject.source,
    )
