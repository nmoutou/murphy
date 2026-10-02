"""La table de rôles : une source réduite à une donnée. Une source nouvelle est une
table, pas un second parser.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from ragcore.core.links import LinkTable
from ragcore.core.models.enums import DocumentType

from .roles import Role

__all__ = ["RoleTable"]


@dataclass(frozen=True)
class RoleTable:
    """Tout ce qu'une source déclare de sa structure XML."""

    roots: tuple[str, ...]
    """Les racines XML connues, dans l'ordre de fusion des facettes (ADR-049) : les
    valeurs multiples d'une métadonnée suivent ce rang. Une autre racine ressort en
    ``unknowns["roots"]``.
    """

    roles: Mapping[str, Role]
    """Un rôle par balise. Une balise absente ressort au bilan du run, comme non
    configurée."""

    content_blocks: Sequence[str] = ()
    """Les balises qui portent le texte, dans l'ordre de lecture, qui fixe les offsets
    des chunks.

    Distinct du rôle ``BODY`` : le rôle dit ce qu'est une balise, cette séquence où
    chercher. Un ``TEXTE_VERSION`` n'a pas de ``BLOC_TEXTUEL`` : son texte vit sous
    ``VISAS``, ``SIGNATAIRES``, ``TP``.
    """

    text_holders: Sequence[str] = ()
    """Les balises qui, dans un bloc de contenu, portent le texte (cf. ``tree.holders``)."""

    title_tags: Sequence[str] = ()
    """Où chaque famille range son titre, par ordre de préférence entre facettes.
    Une balise de rôle ``TITLE`` n'entre pas en métadonnée (ADR-050).
    """

    identifier_tag: str = "ID"
    document_types: Mapping[str, DocumentType] = field(default_factory=dict)
    """Préfixe de l'identifiant → type (``LEGIARTI`` → article). Un préfixe absent fait
    refuser le document."""

    nature_tag: str = "NATURE"
    """Elle a son champ dédié et n'entre pas en métadonnée."""

    uninformative_natures: frozenset[str] = frozenset()
    """En majuscules, elles deviennent ``None`` : JADE écrit toujours ``Texte``, un
    article LEGI ``Article``."""

    meta_containers: Sequence[str] = ()
    """Les seules balises où chercher les métadonnées, pour ne pas aspirer le corps ou
    les liens."""

    meta_renames: Mapping[str, str] = field(default_factory=dict)
    """Balise brute → nom du domaine (``DATE_PUBLI`` → ``date_publication``). Sans
    renommage, la balise entre quand même, sous sa clé chemin-complet."""

    list_keys: frozenset[str] = frozenset()
    """Clés renommées multivaluées, toujours en liste (ADR-049). Une autre clé renommée
    qui reçoit deux valeurs distinctes fait refuser le document."""

    version_tags: frozenset[str] = frozenset()
    """L'axe temporel (``DATE_DEBUT``, ``DATE_FIN``, ``ETAT``). Vide en jurisprudence."""

    transparent: Mapping[str, str] = field(default_factory=dict)
    """Mise en forme : balise → séparateur inséré dans le texte. Traversées : le corps
    des articles LEGI tient entièrement dans des ``<p>``."""

    links: LinkTable | None = None
    """Lue par ``core/links`` : le parser ne réimplémente jamais la mécanique des
    arêtes."""

    link_tags: Sequence[str] = ()
    link_containers: Sequence[str] = ()
    """Les seuls conteneurs des liens structurels : sous ``<VERSIONS>``, un ``LIEN_ART``
    n'est pas une contenance, et en faire une créerait cycles et faux parents."""

    structural_link_tags: Sequence[str] = ()
    version_link_containers: Sequence[str] = ()
    """Les conteneurs des liens de version (``<VERSIONS>``), qui deviennent la chaîne
    ``suivi_par``."""

    version_link_tags: Sequence[str] = ()
    ancestor_containers: Sequence[str] = ()
    ancestor_tags: Sequence[str] = ()
    """``TITRE_TXT``, ``TITRE_TM``…"""

    ancestor_id_attrs: Sequence[str] = ("id_txt", "id")
    """Par ordre de préférence."""

    def role_of(self, tag: str) -> Role | None:
        """``None`` si la table ne la connaît pas : un signal, pas une erreur."""
        return self.roles.get(tag)

    def knows(self, tag: str) -> bool:
        """Sous un rôle, comme mise en forme ou comme racine : la mise en forme n'a pas
        de rôle, mais ``<p>`` n'est pas une inconnue."""
        return tag in self.roles or tag in self.transparent or tag in self.roots
