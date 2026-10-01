"""Le parser générique — **un seul**, pour six sources.

**Ce qu'il n'est pas : une réécriture.** Le parser LEGI était *déjà* générique — sa
mécanique (parcourir l'arbre, relever les blocs de texte, aplatir les métadonnées) ne
contenait pas un mot de LEGI. Ce qu'il contenait de LEGI tenait dans quatre constantes de
module. Ce fichier est le même code, dont les constantes sont devenues un argument.

C'est la mesure du succès de §3 : *une source nouvelle = une table, pas un second
parser*. La jurisprudence n'écrira pas une ligne de ce fichier.

**L'invariant qu'il garantit, et dont le chunker dépend.** ``content`` et
``structure["sections"]`` sont lus par la MÊME fonction (``_text_blocks``), dans le même
ordre. Chaque section est donc un **morceau littéral** de ``content``, et
``content.find(section)`` le retrouve toujours. Deux sources divergentes auraient produit
des ``char_start`` qui ne pointent nulle part — et un offset faux ne lève rien : il
désigne simplement le mauvais passage, et personne ne s'en aperçoit.

**Aucune lemmatisation, et ce n'est pas un allègement — c'est une correction.** L'ancien
``_clean_text`` passait le contenu dans spaCy. Mesuré sur un vrai article :

    avant : « Le directeur général est nommé par décret pour une durée de trois ans »
    après : « directeur général nommer décret durée an »

Ce sac de lemmes partait dans Mongo — donc s'affichait à l'utilisateur comme *source* —
et était embarqué par ``all-mpnet-base-v2``, un modèle de phrases entraîné sur du texte
naturel. Le texte original n'était stocké nulle part : la destruction était irréversible.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from ragcore.core.exceptions import ParseError, ValidationError
from ragcore.core.models import ParsedDocument, RawDocument, SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.core.ports.parser import ParseResult

from .classification import document_type_of, nature_of
from .metadata import collect_metadata
from .normalize import normalize_text
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
    """Interprète un document XML transcrit, guidé par une table de rôles.

    Le connecteur a transcrit l'arbre sans rien comprendre ; la table dit ce que chaque
    balise signifie ; ce parser fait le travail. Aucun des trois ne connaît les deux
    autres.
    """

    def __init__(self, table: RoleTable, source: SourceName) -> None:
        self._table = table
        self._source = source

    @property
    def source_name(self) -> SourceName:
        return self._source

    def parse(self, raw: RawDocument) -> ParseResult:
        """Interprète les facettes d'un document.

        Lève ``ValidationError`` si le document est lisible mais irrecevable (pas
        d'identifiant, identifiant mal formé), ``ParseError`` s'il est illisible. Les
        appelants comptent sur cette distinction : l'une est un refus métier, l'autre une
        panne de lecture, et ``document.invalidated`` ne les compte pas sous la même
        raison.

        Rend un ``ParseResult`` : le document, plus les signaux des balises
        non-configurées — absentes de la table (cascade → metadata ou lien) ou sans
        renommage (→ metadata sous leur clé chemin-complet). Le parser reste PUR : il constate et rend, il ne compte rien.
        """
        try:
            return self._interpret(raw)
        except (ValidationError, ParseError):
            raise
        except Exception as exc:
            raise ParseError(f"Erreur lors du parsing : {exc}") from exc

    def _interpret(self, raw: RawDocument) -> ParseResult:
        facets = self._facets(raw)
        routing = UnconfiguredRouting(
            identifier=self._identifier(facets),
            metadata={},
            references=read_references(facets, self._table),
        )
        sourced = _sourced(facets, raw.payload.get("files", ()))
        collect_metadata(sourced, self._table, routing)
        route_unconfigured(sourced, self._table, routing)
        return ParseResult(
            document=self._document(raw, facets, routing),
            unconfigured_tags=routing.tags,
            unconfigured_keys=tuple(routing.keys),
            unknown_roots=routing.roots,
        )

    def _document(
        self, raw: RawDocument, facets: list[Node], routing: UnconfiguredRouting
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
            metadata=routing.metadata,
            source_files=tuple(raw.payload.get("files", ())),
        )

    # ── Lecture des facettes ───────────────────────────────────────────────────

    def _facets(self, raw: RawDocument) -> list[Node]:
        content = raw.payload.get("content")
        if not isinstance(content, list) or not content:
            raise ParseError("Payload vide ou mal formé : aucune facette à lire")
        return content

    def _identifier(self, facets: list[Node]) -> Identifier:
        """L'identifiant du document, lu dans la balise que la table de rôles désigne."""
        for facet in facets:
            node = first(facet, self._table.identifier_tag)
            if node is None or not node["text"].strip():
                continue

            raw_id = node["text"].strip()
            try:
                return Identifier(raw=raw_id)
            except PydanticValidationError as exc:
                # Sans ce relais, la pydantic.ValidationError échapperait au
                # `except ValidationError` des appelants et se ferait compter comme une
                # erreur de parsing — un refus métier maquillé en panne de lecture.
                raise ValidationError(f"Identifiant invalide : {raw_id!r}") from exc

        raise ValidationError("Identifiant absent du document")

    def _title(self, facets: list[Node]) -> str:
        """Le premier titre trouvé, dans l'ordre de préférence de la table.

        À la fusion, ``TEXTE_VERSION`` apporte ``<TITRE>`` et ``TEXTELR`` n'apporte rien :
        c'est exactement pourquoi les deux doivent être lues ensemble, et pourquoi l'ordre
        de ``title_tags`` est une décision, pas un détail.
        """
        for tag in self._table.title_tags:
            for facet in facets:
                node = first(facet, tag)
                if node is not None and node["text"].strip():
                    return normalize_text(node["text"])
        return ""

    def _content(self, facets: list[Node]) -> str:
        """Le texte réel du document — débalisé, normalisé, et RIEN DE PLUS.

        Un document sans bloc de contenu (une section de plan, mesuré : 0/287 chez LEGI)
        rend la chaîne vide, et le chunker n'en fera aucun chunk. C'est la vérité, pas un
        échec : un nœud de structure n'est pas un porteur de texte.
        """
        return normalize_text(
            "\n\n".join(text for _, text in self._text_blocks(facets) if text.strip())
        )

    def _sections(self, facets: list[Node]) -> list[dict[str, Any]]:
        """Les blocs textuels du document, avec leur chemin structurel.

        **Exactement les mêmes blocs que ``_content``, dans le même ordre.** C'est ce qui
        rend les offsets du chunker vérifiables : chaque section est un morceau littéral
        de ``content``, donc ``content.find(section)`` le retrouve toujours.
        """
        return [
            {"path": path, "text": normalize_text(text)}
            for path, text in self._text_blocks(facets)
            if text.strip()
        ]

    # ── Source UNIQUE de `_content` et `_sections` ─────────────────────────────

    def _text_blocks(self, facets: list[Node]) -> list[tuple[list[str], str]]:
        """Les blocs de texte, dans l'ordre : ``(chemin structurel, texte)``.

        **Les faire diverger de ``_content``, c'est garantir que les offsets des chunks
        pointeront à côté du texte qu'ils prétendent découper.** D'où cette source unique.
        """
        return [
            ([facet["tag"], block_tag], text)
            for facet in facets
            for block_tag in self._table.content_blocks
            for block in find_all(facet, block_tag)
            for holder in holders(block, self._table)
            if (text := text_of(holder, self._table)).strip()
        ]


def _sourced(facets: list[Node], files: Sequence[str]) -> list[SourcedFacet]:
    """Chaque facette avec son fichier : les connecteurs les livrent en listes
    parallèles. Un payload sans fichiers (tests) donne un fichier vide."""
    return [
        (facet, files[index] if index < len(files) else "")
        for index, facet in enumerate(facets)
    ]
