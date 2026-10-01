"""LEGI — **une table, et rien d'autre**.

Tout ce que ``sources/legislatif/parser.py`` savait de LEGI est ici, sous forme de données.
Le parser générique lit cette table ; il ne connaît pas le mot ``BLOC_TEXTUEL``.

C'est la mesure du succès de §3 : *une source nouvelle = une table, pas un second
parser*. Ce fichier ne contient **aucune logique** — pas une boucle, pas une condition.
S'il finit par en contenir, c'est que la mécanique du parser générique était incomplète,
et c'est elle qu'il faudra corriger.

**Les familles LEGI**, mesurées sur les 867 fichiers réels — chacune avec sa source de
titre :

    ARTICLE        NUM       + BLOC_TEXTUEL + LIENS + CONTEXTE
    SECTION_TA     TITRE_TA  + STRUCTURE_TA + CONTEXTE          (aucun contenu)
    TEXTE_VERSION  TITRE     + CONTENU + LIENS
    TEXTELR        —         + STRUCT                            (aucun titre)

``TEXTELR`` n'a AUCUN titre (0/98) et ``TEXTE_VERSION`` aucune structure : ce sont les
deux facettes du même document, et le connecteur les livre ensemble. Le parser les lit
donc comme un tout — c'est ce qui empêche les 98 textes du corpus de finir sans titre.
"""

from ragcore.core.models.enums import DocumentType
from ragcore.sources.generic import Role, RoleTable

from .vocabulary import LEGI_LINK_TABLE

__all__ = ["LEGI_ROLE_TABLE"]


_ROOTS = frozenset({"ARTICLE", "SECTION_TA", "TEXTE_VERSION", "TEXTELR"})

_CONTENT_BLOCKS = ("BLOC_TEXTUEL", "VISAS", "SIGNATAIRES", "TP")
"""Les blocs qui portent le TEXTE.

Un ``ARTICLE`` range le sien sous ``<BLOC_TEXTUEL>`` ; un ``TEXTE_VERSION`` n'a **PAS** de
bloc textuel (mesuré : 0/98) — son texte vit sous ``<VISAS>`` (« Vu le code général… »),
``<SIGNATAIRES>`` et ``<TP>``. Ne chercher que ``BLOC_TEXTUEL`` aurait ingéré les 98
décrets du corpus avec un contenu VIDE, sans qu'une seule exception soit levée.

``<NOTA>`` en est exclu délibérément : une note de bas de page n'est pas le texte du
document, et la fondre dedans polluerait l'embedding avec du hors-sujet.
"""

_TITLE_TAGS = ("TITRE", "TITRE_TA", "NUM")
"""Où chaque famille range son titre. **L'ordre compte** : à la fusion, ``TEXTE_VERSION``
(``TITRE``) l'emporte sur ``TEXTELR``, qui n'en a aucun."""


# ── Le rôle de chaque balise. C'est LA table. ──────────────────────────────────
#
# Les 70 balises mesurées sur le corpus. Une balise absente d'ici ressort en
# `unknowns["balise"]` et fait échouer le golden : rien n'entre en silence.

_ROLES: dict[str, Role] = {
    # Les racines : elles ne portent rien elles-mêmes, elles contiennent.
    **dict.fromkeys(_ROOTS, Role.META),
    # ── BODY : le texte du document ────────────────────────────────────────────
    "BLOC_TEXTUEL": Role.BODY,
    "CONTENU": Role.BODY,
    "VISAS": Role.BODY,
    "SIGNATAIRES": Role.BODY,
    "TP": Role.BODY,
    "TEXTE": Role.BODY,
    "NOTA": Role.BODY,  # lu, mais HORS des content_blocks : cf. ci-dessus
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
    # ── VERSION : l'axe temporel. ABSENT de la jurisprudence. ──────────────────
    "DATE_DEBUT": Role.VERSION,
    "DATE_FIN": Role.VERSION,
    "ETAT": Role.VERSION,
    "VERSION": Role.VERSION,
    "VERSIONS": Role.VERSION,
    "VERSION_A_VENIR": Role.VERSION,
    "VERSIONS_A_VENIR": Role.VERSION,
    "ABRO": Role.VERSION,
    "RECT": Role.VERSION,
    # ── META : tout le reste — le fourre-tout LÉGITIME ─────────────────────────
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
    # Elles portent du texte mais aucune sémantique : leur contenu remonte dans le parent.
    # Ne pas les traverser ferait disparaître le texte qu'elles enveloppent — c'est le cas
    # de TOUT le corps des articles, entièrement contenu dans des <p>.
    "p": "\n\n",
    "br": "\n",
    "blockquote": "\n\n",
    "div": "\n",
    "em": "",
    "font": "",
    "span": "",
    "sup": "",
    # Un tableau lu à plat : chaque cellule est un fragment, chaque ligne un saut. On ne
    # prétend pas restituer la grille — on refuse simplement de perdre son contenu.
    "table": "\n",
    "tbody": "",
    "thead": "",
    "tr": "\n",
    "td": " ",
    "th": " ",
}


_META_RENAMES = {
    # La canonicalisation par type : quelle balise brute devient quel champ du domaine.
    # Une balise absente d'ici n'est PAS perdue — elle entre sous son nom brut, en
    # minuscules. Le renommage est une promotion, pas un péage.
    "ANCIEN_ID": "ancien_id",
    "CID": "chronicle_cid",
    "DATE_DEBUT": "date_debut",
    "DATE_FIN": "date_fin",
    "DATE_PUBLI": "date_publication",
    "DATE_TEXTE": "date_texte",
    "ETAT": "statut",
    "NOR": "nor",
    "NUM": "num",
    "ORIGINE": "origine",
    "TITREFULL": "titre_full",
    "URL": "url",
    "TYPE": "type",
}


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
    # La nature d'un article est « Article » : son type le dit déjà.
    uninformative_natures=frozenset({"ARTICLE"}),
    meta_containers=("META",),
    meta_renames=_META_RENAMES,
    version_tags=frozenset({"DATE_DEBUT", "DATE_FIN", "ETAT"}),
    transparent=_TRANSPARENT,
    links=LEGI_LINK_TABLE,
    link_tags=("LIEN",),
    # Les liens structurels sont cherchés UNIQUEMENT ici — et JAMAIS sous <VERSIONS>, où
    # LIEN_ART désigne les autres versions temporelles du MÊME article. Ce n'est pas une
    # contenance : les émettre créerait des cycles et de faux parents.
    link_containers=("STRUCTURE_TA", "STRUCT"),
    structural_link_tags=("LIEN_ART", "LIEN_SECTION_TA"),
    # …mais ce ne sont pas des scories pour autant : les LIEN_ART sous <VERSIONS> sont
    # l'axe temporel de l'article. Ils sortent sous VERSION_KIND et deviennent la CHAÎNE
    # `succeeded_by` (tri par debut, auto-référence = ancre, mort-nées en latéral).
    version_link_containers=("VERSIONS",),
    version_link_tags=("LIEN_ART",),
    ancestor_containers=("CONTEXTE",),
    ancestor_tags=("TITRE_TXT", "TITRE_TM"),
    ancestor_id_attrs=("id_txt", "id"),
)
"""LEGI, en une donnée. Le parser générique fait le reste."""
