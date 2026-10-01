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

from collections.abc import Iterator
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from ragcore.core.exceptions import ParseError, ValidationError
from ragcore.core.models import ParsedDocument, RawDocument, SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.core.ports.parser import ParseResult

from .classification import document_type_of, nature_of
from .normalize import normalize_text
from .role_table import RoleTable
from .roles import Role
from .structure import read_context, read_references
from .tree import (
    Node,
    find_all,
    find_all_with_path,
    first,
    holders,
    path_key,
    text_of,
    walk_with_path,
)
from .unconfigured import UnconfiguredRouting, route_unconfigured

__all__ = ["GenericParser"]

_COLLECTABLE_ROLES = frozenset({Role.META, Role.VERSION})
"""Les rôles qui entrent en métadonnées : ``META``, et ``VERSION``, qui *est* une
métadonnée, sur l'axe temporel."""


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

        Rend un ``ParseResult`` : le document, plus ce que la cascade a rangé sans que
        la table le lui apprenne (balises non-configurées → metadata ou lien) et les
        signaux associés. Le parser reste PUR : il constate et rend, il ne compte rien.
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
            metadata=self._metadata(facets),
            references=read_references(facets, self._table),
        )
        route_unconfigured(facets, self._table, routing)
        return ParseResult(
            document=self._document(raw, facets, routing),
            unconfigured_tags=tuple(routing.tags),
            unconfigured_keys=tuple(routing.keys),
            unknown_roots=tuple(routing.roots),
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

    def _metadata(self, facets: list[Node]) -> dict[str, Any]:
        """Les métadonnées des conteneurs ``<META>``, canonicalisées par la table.

        Ni le contenu ni les liens n'y sont : ils ont leur place, et la dupliquer ferait
        deux vérités.

        **Une balise absente de ``meta_renames`` n'est pas perdue** — elle entre sous son
        nom brut, en minuscules. Le renommage est une *promotion*, pas un péage : le
        parser LEGI, lui, jetait tout ce qu'il ne savait pas renommer, ce qui faisait de
        la table de renommage un filtre déguisé. Une métadonnée non canonicalisée reste
        une métadonnée.

        **Le rôle décide, pas l'emplacement.** ``<META>`` n'est pas un territoire : un
        ``<LIEN>`` niché dedans reste un lien, et l'aspirer en métadonnée en ferait une
        seconde vérité — la même arête, décrite à deux endroits, qui peuvent diverger.
        Seules les balises de rôle ``META`` (et ``VERSION``, qui *est* une métadonnée, sur
        l'axe temporel) entrent ici. C'est précisément à ça que sert la table de rôles :
        sans elle, on rangeait par position dans l'arbre, ce qui est un pari sur la forme
        du XML plutôt qu'une lecture de son sens.

        **Sauf l'identifiant et la nature.** Ils ont leur champ dédié
        (``ParsedDocument.identifier``, ``ParsedDocument.nature``) : les recopier ici en
        ferait, là encore, une seconde vérité.

        **La clé est le CHEMIN COMPLET, plus le nom de balise nu** (ADR-022 §3). L'ancien
        ``node["tag"].lower()`` faisait s'écraser deux balises homonymes à deux endroits
        de l'arbre — premier arrivé gagne, en silence. Le chemin rend la clé injective
        par construction : la collision n'est plus gérée, elle est impossible. Seule la
        **promotion** (``meta_renames``) garde un nom court : c'est une décision de la
        table, premier-arrivé-gagne assumé (l'ordre de préférence des facettes).
        """
        metadata: dict[str, Any] = {}
        for facet in facets:
            for node, path in self._meta_leaves(facet):
                key = self._table.meta_renames.get(node["tag"], path_key(path))
                if key not in metadata:
                    metadata[key] = node["text"].strip()
        return metadata

    def _meta_leaves(self, facet: Node) -> Iterator[tuple[Node, tuple[str, ...]]]:
        """Les feuilles collectables des conteneurs ``<META>``, avec leur chemin."""
        for container in self._table.meta_containers:
            for meta, meta_path in find_all_with_path(facet, container):
                yield from (
                    (node, path)
                    for node, path in walk_with_path(meta, meta_path[:-1])
                    if self._is_collectable(node)
                )

    def _is_collectable(self, node: Node) -> bool:
        """Une feuille non vide, de rôle collectable, qui n'a pas son champ dédié
        (l'identifiant, la nature)."""
        return (
            not node["children"]
            and bool(node["text"].strip())
            and node["tag"] not in (self._table.identifier_tag, self._table.nature_tag)
            and self._table.role_of(node["tag"]) in _COLLECTABLE_ROLES
        )

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
