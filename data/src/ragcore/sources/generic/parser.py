"""Le parser générique, unique pour toutes les sources, guidé par une table de rôles.

Invariant dont dépend le chunker : ``content`` et ``structure["sections"]`` viennent de
la même fonction (``_text_blocks``), dans le même ordre, donc chaque section est un
morceau littéral de ``content``.

Aucune lemmatisation : le contenu s'affiche à l'utilisateur et part dans un modèle de
phrases entraîné sur du texte naturel.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from ragcore.core.exceptions import CollisionError, ParseError, ValidationError
from ragcore.core.models import ParsedDocument, RawDocument, SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.core.ports.parser import ParseResult

from .classification import document_type_of, nature_of
from .metadata import collect_metadata
from .normalize import normalize_text
from .occurrences import resolve
from .role_table import RoleTable
from .structure import read_context, read_references
from .tree import (
    Node,
    find_all,
    first,
    holders,
    text_of,
)
from .unconfigured import SourcedFacet, UnconfiguredRouting, route_unconfigured

__all__ = ["GenericParser"]


class GenericParser:
    def __init__(self, table: RoleTable, source: SourceName) -> None:
        self._table = table
        self._source = source

    @property
    def source_name(self) -> SourceName:
        return self._source

    def parse(self, raw: RawDocument) -> ParseResult:
        """Lève ``ValidationError`` si le document est lisible mais irrecevable (dont
        ``CollisionError``, ADR-049), ``ParseError`` s'il est illisible : un refus métier
        et une panne de lecture ne sont pas comptés sous la même raison.

        Pur : les signaux non configurés et les collisions sont rendus, pas comptés.
        """
        try:
            return self._interpret(raw)
        except (ValidationError, ParseError):
            raise
        except Exception as exc:
            raise ParseError(f"Erreur lors du parsing : {exc}") from exc

    def _interpret(self, raw: RawDocument) -> ParseResult:
        sourced = _ordered(
            _sourced(self._facets(raw), raw.payload.get("files", ())), self._table
        )
        facets = [facet for facet, _ in sourced]
        routing = UnconfiguredRouting(
            identifier=self._identifier(facets),
            references=read_references(facets, self._table),
        )
        collect_metadata(sourced, self._table, routing)
        route_unconfigured(sourced, self._table, routing)
        resolution = resolve(
            routing.occurrences,
            self._table,
            self._source,
            routing.identifier.serialize(),
        )
        if resolution.blocking:
            raise CollisionError(
                f"Collision non configurée sur {list(resolution.blocking)}",
                resolution.collisions,
            )
        return ParseResult(
            document=self._document(raw, facets, routing, resolution.metadata),
            unconfigured_tags=routing.tags,
            unconfigured_links=routing.links,
            unknown_roots=routing.roots,
            collisions=resolution.collisions,
        )

    def _document(
        self,
        raw: RawDocument,
        facets: list[Node],
        routing: UnconfiguredRouting,
        metadata: dict[str, Any],
    ) -> ParsedDocument:
        return ParsedDocument(
            identifier=routing.identifier,
            source=self._source,
            document_type=document_type_of(routing.identifier, self._table),
            nature=nature_of(facets, self._table),
            title=self._title(facets),
            content=self._content(facets),
            structure={
                "references": routing.references,
                "sections": self._sections(facets),
                "context": read_context(facets, self._table),
            },
            metadata=metadata,
            source_files=tuple(raw.payload.get("files", ())),
        )

    # ── Lecture des facettes ───────────────────────────────────────────────────

    def _facets(self, raw: RawDocument) -> list[Node]:
        content = raw.payload.get("content")
        if not isinstance(content, list) or not content:
            raise ParseError("Payload vide ou mal formé : aucune facette à lire")
        return content

    def _identifier(self, facets: list[Node]) -> Identifier:
        for facet in facets:
            node = first(facet, self._table.identifier_tag)
            if node is None or not node["text"].strip():
                continue

            raw_id = node["text"].strip()
            try:
                return Identifier(raw=raw_id)
            except PydanticValidationError as exc:
                # Sinon l'erreur pydantic serait comptée en panne de lecture
                raise ValidationError(f"Identifiant invalide : {raw_id!r}") from exc

        raise ValidationError("Identifiant absent du document")

    def _title(self, facets: list[Node]) -> str:
        """Le premier titre trouvé, dans l'ordre de préférence de la table."""
        for tag in self._table.title_tags:
            for facet in facets:
                node = first(facet, tag)
                if node is not None and node["text"].strip():
                    return normalize_text(node["text"])
        return ""

    def _content(self, facets: list[Node]) -> str:
        """Débalisé, normalisé, rien de plus. Vide pour une section de plan, qui ne
        porte pas de texte."""
        return normalize_text(
            "\n\n".join(text for _, text in self._text_blocks(facets) if text.strip())
        )

    def _sections(self, facets: list[Node]) -> list[dict[str, Any]]:
        """Les mêmes blocs que ``_content``, dans le même ordre, avec leur chemin."""
        return [
            {"path": path, "text": normalize_text(text)}
            for path, text in self._text_blocks(facets)
            if text.strip()
        ]

    # ── Source unique de `_content` et `_sections` ─────────────────────────────

    def _text_blocks(self, facets: list[Node]) -> list[tuple[list[str], str]]:
        """``(chemin structurel, texte)``, dans l'ordre."""
        return [
            ([facet["tag"], block_tag], text)
            for facet in facets
            for block_tag in self._table.content_blocks
            for block in find_all(facet, block_tag)
            for holder in holders(block, self._table)
            if (text := text_of(holder, self._table)).strip()
        ]


def _ordered(sourced: list[SourcedFacet], table: RoleTable) -> list[SourcedFacet]:
    """Dans l'ordre de ``table.roots``, qui fixe celui des valeurs d'une clé (ADR-049).

    Sans ordre possible (racine non déclarée ou partagée), le document est refusé
    plutôt que trié au hasard.
    """
    if len(sourced) <= 1:
        return sourced
    roots = [facet["tag"] for facet, _ in sourced]
    if len(set(roots)) < len(roots) or not set(roots) <= set(table.roots):
        raise ValidationError(
            f"Ordre des facettes indéterminé : racines {roots}, "
            f"ordre déclaré {list(table.roots)}"
        )
    return sorted(sourced, key=lambda pair: table.roots.index(pair[0]["tag"]))


def _sourced(facets: list[Node], files: Sequence[str]) -> list[SourcedFacet]:
    """Les connecteurs livrent facettes et fichiers en listes parallèles. Sans fichiers
    (tests), le fichier est vide."""
    return [
        (facet, files[index] if index < len(files) else "")
        for index, facet in enumerate(facets)
    ]
