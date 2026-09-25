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

import re
from collections.abc import Iterator, Sequence
from typing import Any

from ragcore.core.exceptions import ParseError, ValidationError
from ragcore.core.links import HEURISTIC_KIND, VERSION_KIND
from ragcore.core.models import ParsedDocument, RawDocument, SourceName
from ragcore.core.models.identifiers import SourceIdentifier
from ragcore.core.ports.parser import ParseResult

from .normalize import normalize_text
from .role_table import RoleTable
from .roles import Role

__all__ = ["GenericParser"]

_DILA_ID = re.compile(r"[A-Z]{8}[0-9]{12}\Z")
"""La forme d'un identifiant DILA (``LEGIARTI000006219120``) — le même motif que
``importation.validation.format_regex`` dans ``parameters.yml``.

C'est le déclencheur de la règle 4 de la cascade (cadrage B-00-d) : du duck-typing sur
la VALEUR, jamais sur le nom d'attribut. Mesuré sur le corpus : ``origine="LEGI"`` ne
matche pas (à raison), et les porteurs légitimes hors liens (``VERSION``, ``TITRE_TM``,
l'auto-``cid`` de ``TEXTE``) sont tous des balises CONNUES de la table — ils n'arrivent
jamais jusqu'à l'heuristique, qui ne voit que le vocabulaire non-configuré.
"""


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
        panne de lecture, et le manifest ne les inscrit pas sous la même raison.

        Rend un ``ParseResult`` : le document, plus ce que la cascade a rangé sans que
        la table le lui apprenne (balises non-configurées → metadata ou lien) et les
        signaux associés. Le parser reste PUR : il constate et rend, il ne compte rien.
        """
        try:
            facets = self._facets(raw)
            identifier = self._identifier(facets)
            metadata = self._metadata(facets)
            references = self._references(facets)

            unconfigured_tags, unconfigured_keys, unknown_roots = (
                self._route_unconfigured(facets, identifier, metadata, references)
            )

            document = ParsedDocument(
                identifier=identifier,
                source=self._source,
                owner_id=raw.owner_id,
                title=self._title(facets),
                content=self._content(facets),
                structure={
                    "references": references,
                    "sections": self._sections(facets),
                    "context": self._context(facets),
                },
                metadata=metadata,
                source_files=tuple(raw.payload.get("files", ())),
            )
            return ParseResult(
                document=document,
                unconfigured_tags=unconfigured_tags,
                unconfigured_keys=unconfigured_keys,
                unknown_roots=unknown_roots,
            )
        except (ValidationError, ParseError):
            raise
        except Exception as exc:
            raise ParseError(f"Erreur lors du parsing : {exc}") from exc

    # ── La cascade des trois portes : ce que la table ne sait pas ranger ─────────

    def _route_unconfigured(
        self,
        facets: list[dict[str, Any]],
        identifier: SourceIdentifier,
        metadata: dict[str, Any],
        references: list[dict[str, Any]],
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        """Route chaque balise NON-CONFIGURÉE vers sa porte (cadrage B-00-d).

        Il n'y a plus d'« unknown » : une balise que la table ne connaît pas est une
        donnée dont on n'a pas encore promu le nom, et elle a une DESTINATION —

        - sa valeur a la forme d'un identifiant DILA et n'est pas le document lui-même
          (règle auto-id) → **porte liens** : une référence ``HEURISTIC_KIND``, que
          ``core/links`` traduira en arête ``references`` ;
        - sinon → **porte metadata**, sous sa clé chemin-complet (injective, ADR-022 §3).

        Les balises CONNUES n'arrivent jamais ici (``knows()`` les écarte) : c'est la
        cascade du cadrage, où la table tranche AVANT l'heuristique — ``VERSION`` et les
        titres sont déclarés, ils ne peuvent pas devenir de faux liens.

        Rien ne disparaît, et rien n'est compté ici : le SIGNAL (balises et racines
        non-configurées) sort dans la valeur de retour, et c'est le site de parse — qui
        tient la télémétrie — qui le déclare. Pureté du parser préservée.
        """
        tags: list[str] = []
        keys: list[str] = []
        roots: list[str] = []

        for facet in facets:
            if facet["tag"] not in self._table.roots and facet["tag"] not in roots:
                roots.append(facet["tag"])

            for node, path in _walk_with_path(facet):
                if self._table.knows(node["tag"]):
                    continue
                if node["tag"] not in tags:
                    tags.append(node["tag"])

                key_base = _path_key(path)
                self._route_values(
                    node, key_base, identifier, metadata, references, keys
                )

        return tuple(tags), tuple(keys), tuple(roots)

    def _route_values(  # noqa: PLR0913 — les six pièces du routage voyagent ensemble ; les grouper cacherait la cascade
        self,
        node: dict[str, Any],
        key_base: str,
        identifier: SourceIdentifier,
        metadata: dict[str, Any],
        references: list[dict[str, Any]],
        keys: list[str],
    ) -> None:
        """Les VALEURS d'un nœud non-configuré : attributs, puis texte de feuille."""
        for name, value in node["attrib"].items():
            text = str(value).strip()
            if not text:
                continue
            if self._is_reference_value(text, identifier):
                references.append(
                    {"kind": HEURISTIC_KIND, "id": text, "tag": node["tag"]}
                )
                continue
            key = f"{key_base}_{name.lower()}"
            if key not in metadata:
                metadata[key] = text
                keys.append(key)

        text = node["text"].strip()
        if not text or node["children"]:
            return
        if self._is_reference_value(text, identifier):
            references.append({"kind": HEURISTIC_KIND, "id": text, "tag": node["tag"]})
            return
        if key_base not in metadata:
            metadata[key_base] = text
            keys.append(key_base)

    @staticmethod
    def _is_reference_value(value: str, identifier: SourceIdentifier) -> bool:
        """Règles 3-4 de la cascade : la forme DILA, sauf soi-même.

        La comparaison à l'identité du document courant est STRUCTURELLE — pas une liste
        noire : un ``cid`` qui porte l'identifiant du document décrit le document, il ne
        pointe vers rien.
        """
        return bool(_DILA_ID.fullmatch(value)) and value != identifier.raw

    # ── Lecture des facettes ───────────────────────────────────────────────────

    def _facets(self, raw: RawDocument) -> list[dict[str, Any]]:
        content = raw.payload.get("content")
        if not isinstance(content, list) or not content:
            raise ParseError("Payload vide ou mal formé : aucune facette à lire")
        return content

    def _identifier(self, facets: list[dict[str, Any]]) -> SourceIdentifier:
        """L'identifiant, typé par la source (``identifier_for`` de sa ``LinkTable``)."""
        for facet in facets:
            node = _first(facet, self._table.identifier_tag)
            if node is None or not node["text"].strip():
                continue

            raw_id = node["text"].strip()
            try:
                return self._build_identifier(raw_id)
            except ValidationError:
                raise
            except Exception as exc:
                # Sans ce relais, la pydantic.ValidationError échapperait au
                # `except ValidationError` des appelants et se ferait compter comme une
                # erreur de parsing — un refus métier maquillé en panne de lecture.
                raise ValidationError(f"Identifiant invalide : {raw_id!r}") from exc

        raise ValidationError("Identifiant absent du document")

    def _build_identifier(self, raw_id: str) -> SourceIdentifier:
        links = self._table.links
        if links is None or links.identifier_for is None:
            raise ValidationError(
                "La table de rôles ne sait pas typer les identifiants de cette source"
            )
        return links.identifier_for(raw_id)

    def _title(self, facets: list[dict[str, Any]]) -> str:
        """Le premier titre trouvé, dans l'ordre de préférence de la table.

        À la fusion, ``TEXTE_VERSION`` apporte ``<TITRE>`` et ``TEXTELR`` n'apporte rien :
        c'est exactement pourquoi les deux doivent être lues ensemble, et pourquoi l'ordre
        de ``title_tags`` est une décision, pas un détail.
        """
        for tag in self._table.title_tags:
            for facet in facets:
                node = _first(facet, tag)
                if node is not None and node["text"].strip():
                    return normalize_text(node["text"])
        return ""

    def _content(self, facets: list[dict[str, Any]]) -> str:
        """Le texte réel du document — débalisé, normalisé, et RIEN DE PLUS.

        Un document sans bloc de contenu (une section de plan, mesuré : 0/287 chez LEGI)
        rend la chaîne vide, et le chunker n'en fera aucun chunk. C'est la vérité, pas un
        échec : un nœud de structure n'est pas un porteur de texte.
        """
        return normalize_text(
            "\n\n".join(text for _, text in self._text_blocks(facets) if text.strip())
        )

    # ── La structure ───────────────────────────────────────────────────────────

    def _references(self, facets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Les liens déclarés, **BRUTS** — le parser ne les type pas.

        Il rend le vocabulaire de la source tel quel (``typelien``, ``sens``, ``id``) ;
        c'est ``core/links`` qui le traduit, et qui déclare ce qu'il ne sait pas traduire.
        Typer ici mettrait la table de traduction dans deux modules à la fois — et c'est
        exactement ainsi qu'elles divergent.
        """
        references: list[dict[str, Any]] = []

        for facet in facets:
            for tag in self._table.link_tags:
                for lien in _find_all(facet, tag):
                    references.append(
                        {
                            "kind": tag,
                            "id": lien["attrib"].get("id", ""),
                            "typelien": lien["attrib"].get("typelien", ""),
                            "sens": lien["attrib"].get("sens", ""),
                            "label": normalize_text(_text_of(lien, self._table)),
                        }
                    )

            # Les liens STRUCTURELS : cherchés UNIQUEMENT dans leurs conteneurs déclarés.
            # Sous <VERSIONS>, un LIEN_ART désigne les autres versions du MÊME article —
            # pas une contenance : il a son propre circuit, juste en dessous.
            for container in self._table.link_containers:
                for parent in _find_all(facet, container):
                    for tag in self._table.structural_link_tags:
                        for lien in _find_all(parent, tag):
                            references.append(
                                {
                                    "kind": tag,
                                    "id": lien["attrib"].get("id", ""),
                                    "label": normalize_text(
                                        _text_of(lien, self._table)
                                    ),
                                }
                            )

            # Les liens de VERSION : l'axe temporel, sous son kind dédié. La datation
            # (debut/fin/etat/num) voyage avec la référence — elle finira sur l'arête.
            for container in self._table.version_link_containers:
                for parent in _find_all(facet, container):
                    for tag in self._table.version_link_tags:
                        for lien in _find_all(parent, tag):
                            references.append(
                                {
                                    "kind": VERSION_KIND,
                                    "id": lien["attrib"].get("id", ""),
                                    **{
                                        name: str(value)
                                        for name, value in lien["attrib"].items()
                                        if name != "id" and str(value).strip()
                                    },
                                }
                            )

        return references

    def _context(self, facets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Les ANCÊTRES du document.

        ``<CONTEXTE>`` déclare la *fermeture transitive* de la contenance — jusqu'à neuf
        niveaux d'un coup, pas seulement le parent direct. C'est la raison d'être de
        ``core/services/relation_reduction`` : l'union de cette fermeture et de l'arbre
        déclaré par les sections doit être réduite pour redonner l'arbre.
        """
        context: list[dict[str, Any]] = []

        for facet in facets:
            for container in self._table.ancestor_containers:
                for parent in _find_all(facet, container):
                    for tag in self._table.ancestor_tags:
                        for node in _find_all(parent, tag):
                            ancestor = _first_attr(node, self._table.ancestor_id_attrs)
                            if ancestor:
                                context.append(
                                    {
                                        "kind": tag,
                                        "id": ancestor,
                                        "label": normalize_text(node["text"]),
                                    }
                                )

        return context

    def _sections(self, facets: list[dict[str, Any]]) -> list[dict[str, Any]]:
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

    def _metadata(self, facets: list[dict[str, Any]]) -> dict[str, Any]:
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

        **Sauf l'identifiant.** Il a son champ dédié (``ParsedDocument.identifier``) : le
        recopier ici en ferait, là encore, une seconde vérité.

        **La clé est le CHEMIN COMPLET, plus le nom de balise nu** (ADR-022 §3). L'ancien
        ``node["tag"].lower()`` faisait s'écraser deux balises homonymes à deux endroits
        de l'arbre — premier arrivé gagne, en silence. Le chemin rend la clé injective
        par construction : la collision n'est plus gérée, elle est impossible. Seule la
        **promotion** (``meta_renames``) garde un nom court : c'est une décision de la
        table, premier-arrivé-gagne assumé (l'ordre de préférence des facettes).
        """
        metadata: dict[str, Any] = {}
        collectable = {Role.META, Role.VERSION}

        for facet in facets:
            for container in self._table.meta_containers:
                for meta, meta_path in _find_all_with_path(facet, container):
                    for node, path in _walk_with_path(meta, meta_path[:-1]):
                        if node["children"] or not node["text"].strip():
                            continue
                        if node["tag"] == self._table.identifier_tag:
                            continue
                        if self._table.role_of(node["tag"]) not in collectable:
                            continue
                        key = self._table.meta_renames.get(node["tag"], _path_key(path))
                        if key not in metadata:
                            metadata[key] = node["text"].strip()

        return metadata

    # ── Source UNIQUE de `_content` et `_sections` ─────────────────────────────

    def _text_blocks(self, facets: list[dict[str, Any]]) -> list[tuple[list[str], str]]:
        """Les blocs de texte, dans l'ordre : ``(chemin structurel, texte)``.

        **Les faire diverger de ``_content``, c'est garantir que les offsets des chunks
        pointeront à côté du texte qu'ils prétendent découper.** D'où cette source unique.
        """
        blocks: list[tuple[list[str], str]] = []

        for facet in facets:
            for block_tag in self._table.content_blocks:
                for block in _find_all(facet, block_tag):
                    holders = _holders(block, self._table)
                    for holder in holders:
                        text = _text_of(holder, self._table)
                        if text.strip():
                            blocks.append(([facet["tag"], block_tag], text))

        return blocks


# ── Parcours d'arbre : le connecteur transcrit, ces fonctions relisent ──────────


def _holders(block: dict[str, Any], table: RoleTable) -> list[dict[str, Any]]:
    """Les porteurs de texte d'un bloc — ou le bloc lui-même s'il n'en a pas.

    ``<BLOC_TEXTUEL>`` enveloppe son texte dans ``<CONTENU>`` ; ``<VISAS>`` le porte
    directement. On descend s'il y a un porteur, sinon on lit le bloc.
    """
    for holder_tag in table.text_holders:
        found = _find_all(block, holder_tag)
        if found:
            return found
    return [block]


def _walk(tree: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yield tree
    for child in tree["children"]:
        yield from _walk(child)


def _walk_with_path(
    tree: dict[str, Any], prefix: tuple[str, ...] = ()
) -> Iterator[tuple[dict[str, Any], tuple[str, ...]]]:
    """Comme ``_walk``, mais chaque nœud arrive avec son CHEMIN depuis la racine.

    C'est la pièce qui rend l'aplatissement par chemin complet possible (ADR-022 §3) :
    ``_walk`` yield des nœuds nus, et une clé construite sur le seul tag produit la
    collision « premier arrivé gagne » — deux ``<NUM>`` à deux endroits de l'arbre
    s'écrasent. Le chemin rend la clé injective par construction.
    """
    path = (*prefix, tree["tag"])
    yield tree, path
    for child in tree["children"]:
        yield from _walk_with_path(child, path)


def _path_key(path: tuple[str, ...]) -> str:
    """Un chemin de balises → la clé plate canonique (snake_case, jointure ``_``).

    ``("ARTICLE", "META", …, "NUM")`` → ``article_meta_…_num``. La MÊME convention que
    ``title_mapping.sources`` dans ``parameters.yml`` — elle préexistait dans la conf,
    le parser la rejoint.
    """
    return "_".join(tag.lower() for tag in path)


def _find_all_with_path(
    tree: dict[str, Any], tag: str
) -> list[tuple[dict[str, Any], tuple[str, ...]]]:
    return [(node, path) for node, path in _walk_with_path(tree) if node["tag"] == tag]


def _find_all(tree: dict[str, Any], tag: str) -> list[dict[str, Any]]:
    return [node for node in _walk(tree) if node["tag"] == tag]


def _first(tree: dict[str, Any], tag: str) -> dict[str, Any] | None:
    return next((node for node in _walk(tree) if node["tag"] == tag), None)


def _first_attr(node: dict[str, Any], names: Sequence[str]) -> str:
    """Le premier attribut présent, dans l'ordre de préférence donné."""
    for name in names:
        value = node["attrib"].get(name)
        if value:
            return str(value)
    return ""


def _text_of(node: dict[str, Any], table: RoleTable) -> str:
    """Le texte d'un nœud, en traversant les balises de mise en forme.

    On ne descend **PAS** dans les balises non transparentes : leur texte est un autre
    champ, pas une continuation de celui-ci. Descendre partout ferait entrer les titres
    et les libellés de liens dans le corps du document.
    """
    parts: list[str] = []

    def visit(current: dict[str, Any]) -> None:
        if current["text"].strip():
            parts.append(current["text"].strip())
        for child in current["children"]:
            separator = table.transparent.get(child["tag"])
            if separator is not None:
                visit(child)
                parts.append(separator)
            if child["tail"].strip():
                parts.append(child["tail"].strip())

    visit(node)
    return " ".join(parts)
