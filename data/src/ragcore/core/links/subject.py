"""Le document dont on extrait les liens — et la seule fabrique de ``Relation``."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..models.enums import SourceName
from ..models.identifiers import Identifier
from ..models.relation import Relation
from .vocabulary import RelationVerb

__all__ = ["LinkSubject"]


@dataclass(frozen=True)
class LinkSubject:
    """Le document dont on extrait les liens."""

    current: Identifier
    source: SourceName

    def relation(
        self,
        edge_source: Identifier,
        edge_target: Identifier,
        relation_verb: RelationVerb,
        metadata: Mapping[str, Any],
    ) -> Relation:
        """Les métadonnées vides ne sont pas écrites."""
        return Relation(
            source_identifier=edge_source,
            target_identifier=edge_target,
            relation_type=relation_verb,
            source=self.source,
            metadata={key: value for key, value in metadata.items() if value},
        )
