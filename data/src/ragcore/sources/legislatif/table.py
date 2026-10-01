"""La table de rôles de LEGI. Aucune logique ici : s'il en faut, c'est le parser
générique qui est incomplet.

Les familles LEGI, avec leur titre :

    ARTICLE        NUM       + BLOC_TEXTUEL + LIENS + CONTEXTE
    SECTION_TA     TITRE_TA  + STRUCTURE_TA + CONTEXTE          (aucun contenu)
    TEXTE_VERSION  TITRE     + CONTENU + LIENS
    TEXTELR        —         + STRUCT                            (aucun titre)

``TEXTE_VERSION`` et ``TEXTELR`` sont les deux facettes d'un même texte, lues ensemble.
"""

from ragcore.core.models.enums import DocumentType
from ragcore.sources.generic import Role, RoleTable

from .vocabulary import LEGI_LINK_TABLE

__all__ = ["LEGI_ROLE_TABLE"]


_ROOTS = ("TEXTE_VERSION", "TEXTELR", "ARTICLE", "SECTION_TA")
"""Dans l'ordre de fusion des facettes : ``TEXTE_VERSION``, qui porte le titre, passe
avant ``TEXTELR`` (ADR-049)."""

_CONTENT_BLOCKS = ("BLOC_TEXTUEL", "VISAS", "SIGNATAIRES", "TP")
"""Un ``TEXTE_VERSION`` n'a pas de ``<BLOC_TEXTUEL>`` : son texte vit sous ``<VISAS>``,
``<SIGNATAIRES>`` et ``<TP>``.

``<NOTA>`` est exclu : une note de bas de page polluerait l'embedding.
"""

_TITLE_TAGS = ("TITRE", "TITRE_TA", "NUM")
"""L'ordre compte : à la fusion, ``TITRE`` l'emporte."""


# ── Le rôle de chaque balise ───────────────────────────────────────────────────
#
# Une balise absente d'ici ressort au bilan et fait échouer le golden.

_ROLES: dict[str, Role] = {
    **dict.fromkeys(_ROOTS, Role.META),
    # ── BODY : le texte du document ────────────────────────────────────────────
    "BLOC_TEXTUEL": Role.BODY,
    "CONTENU": Role.BODY,
    "VISAS": Role.BODY,
    "SIGNATAIRES": Role.BODY,
    "TP": Role.BODY,
    "TEXTE": Role.BODY,
    "NOTA": Role.BODY,  # hors des content_blocks : cf. ci-dessus
    # ── LINK : les arêtes ──────────────────────────────────────────────────────
    "LIENS": Role.LINK,
    "LIEN": Role.LINK,
    "LIEN_ART": Role.LINK,
    "LIEN_SECTION_TA": Role.LINK,
    "LIEN_TXT": Role.LINK,
    "CONTEXTE": Role.LINK,
    "TITRE_TXT": Role.LINK,
    "TITRE_TM": Role.LINK,
    "TM": Role.LINK,
    "STRUCT": Role.LINK,
    "STRUCTURE_TA": Role.LINK,
    # ── VERSION : l'axe temporel ───────────────────────────────────────────────
    "DATE_DEBUT": Role.VERSION,
    "DATE_FIN": Role.VERSION,
    "ETAT": Role.VERSION,
    "VERSION": Role.VERSION,
    "VERSIONS": Role.VERSION,
    "VERSION_A_VENIR": Role.VERSION,
    "VERSIONS_A_VENIR": Role.VERSION,
    "ABRO": Role.VERSION,
    "RECT": Role.VERSION,
    # ── META : tout le reste ───────────────────────────────────────────────────
    "META": Role.META,
    "META_ARTICLE": Role.META,
    "META_COMMUN": Role.META,
    "META_SPEC": Role.META,
    "META_TEXTE_CHRONICLE": Role.META,
    "META_TEXTE_VERSION": Role.META,
    "ID": Role.META,
    "TITRE": Role.META,
    "TITRE_TA": Role.META,
    "NUM": Role.META,
    "ANCIEN_ID": Role.META,
    "AUTORITE": Role.META,
    "CID": Role.META,
    "DATE_PUBLI": Role.META,
    "DATE_TEXTE": Role.META,
    "DERNIERE_MODIFICATION": Role.META,
    "MINISTERE": Role.META,
    "NATURE": Role.META,
    "NOR": Role.META,
    "NUM_PARUTION": Role.META,
    "NUM_SEQUENCE": Role.META,
    "ORIGINE": Role.META,
    "ORIGINE_PUBLI": Role.META,
    "PAGE_DEB_PUBLI": Role.META,
    "PAGE_FIN_PUBLI": Role.META,
    "TITREFULL": Role.META,
    "TYPE": Role.META,
    "URL": Role.META,
}


_TRANSPARENT = {
    "p": "\n\n",
    "br": "\n",
    "blockquote": "\n\n",
    "div": "\n",
    "em": "",
    "font": "",
    "span": "",
    "sup": "",
    # Un tableau lu à plat : on ne restitue pas la grille, on garde son contenu
    "table": "\n",
    "tbody": "",
    "thead": "",
    "tr": "\n",
    "td": " ",
    "th": " ",
}


_META_RENAMES = {
    "ANCIEN_ID": "ancien_id",
    "CID": "chronicle_cid",
    "DATE_DEBUT": "date_debut",
    "DATE_FIN": "date_fin",
    "DATE_PUBLI": "date_publication",
    "DATE_TEXTE": "date_texte",
    "DERNIERE_MODIFICATION": "derniere_modification",
    "ETAT": "statut",
    "NOR": "nor",
    "NUM": "num",
    "NUM_PARUTION": "num_parution",
    "NUM_SEQUENCE": "num_sequence",
    "ORIGINE": "origine",
    "ORIGINE_PUBLI": "origine_publication",
    "PAGE_DEB_PUBLI": "page_debut_publication",
    "PAGE_FIN_PUBLI": "page_fin_publication",
    "TITREFULL": "titre_full",
    "URL": "url",
    "TYPE": "type",
    "VERSION_A_VENIR": "versions_a_venir",
}

_LIST_KEYS = frozenset({"url", "versions_a_venir"})
"""ADR-049. ``url`` : chaque facette d'un texte donne le chemin de son propre fichier.
``versions_a_venir`` : plusieurs dates dans une même facette."""


LEGI_ROLE_TABLE = RoleTable(
    roots=_ROOTS,
    roles=_ROLES,
    content_blocks=_CONTENT_BLOCKS,
    text_holders=("CONTENU",),
    title_tags=_TITLE_TAGS,
    identifier_tag="ID",
    document_types={
        "LEGIARTI": DocumentType.ARTICLE,
        "LEGITEXT": DocumentType.TEXTE,
        "LEGISCTA": DocumentType.SECTION,
    },
    # Son type le dit déjà
    uninformative_natures=frozenset({"ARTICLE"}),
    meta_containers=("META",),
    meta_renames=_META_RENAMES,
    list_keys=_LIST_KEYS,
    version_tags=frozenset({"DATE_DEBUT", "DATE_FIN", "ETAT"}),
    transparent=_TRANSPARENT,
    links=LEGI_LINK_TABLE,
    link_tags=("LIEN",),
    # Jamais sous <VERSIONS>, où LIEN_ART désigne une autre version du même article
    link_containers=("STRUCTURE_TA", "STRUCT"),
    structural_link_tags=("LIEN_ART", "LIEN_SECTION_TA"),
    # Ceux-là deviennent la chaîne `succeeded_by`
    version_link_containers=("VERSIONS",),
    version_link_tags=("LIEN_ART",),
    ancestor_containers=("CONTEXTE",),
    ancestor_tags=("TITRE_TXT", "TITRE_TM"),
    ancestor_id_attrs=("id_txt", "id"),
)
