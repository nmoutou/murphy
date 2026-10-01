"""Les tables de rôles de la jurisprudence : une par forme de document, pas par base.

    TEXTE_JURI_JUDI     CAPP, CASS, INCA   (judiciaire : cours d'appel, Cassation)
    TEXTE_JURI_ADMIN    JADE               (administratif : Conseil d'État, CAA, TA)
    TEXTE_JURI_CONSTIT  CONSTIT            (Conseil constitutionnel)

La structure est celle de LEGI ; seul ``META_SPEC`` change. Pas de versions (un arrêt
est rendu une fois), pas de structure (un arrêt ne contient pas d'arrêts), pas de cible
de lien identifiée (cf. ``vocabulary.py``).
"""

from dataclasses import replace

from ragcore.core.models.enums import DocumentType
from ragcore.sources.generic import Role, RoleTable

from .vocabulary import JURI_LINK_TABLE

__all__ = [
    "JURI_ADMIN_ROLE_TABLE",
    "JURI_CONSTIT_ROLE_TABLE",
    "JURI_JUDI_ROLE_TABLE",
    "ROLE_TABLE_BY_ROOT",
]


# ── Le socle commun aux trois racines ──────────────────────────────────────────
#
# Ce que toute décision porte : le `META_COMMUN` de LEGI.

_COMMON_ROLES: dict[str, Role] = {
    # Structure documentaire
    "META": Role.META,
    "META_COMMUN": Role.META,
    "META_SPEC": Role.META,
    "META_JURI": Role.META,
    "TEXTE": Role.BODY,
    # Le corps
    "BLOC_TEXTUEL": Role.BODY,
    "CONTENU": Role.BODY,
    # Identité et provenance
    "ID": Role.META,
    "ANCIEN_ID": Role.META,
    "ORIGINE": Role.META,
    "URL": Role.META,
    "NATURE": Role.META,
    "ECLI": Role.META,
    # Ce que toute décision porte
    "TITRE": Role.META,
    "DATE_DEC": Role.META,
    "JURIDICTION": Role.META,
    "NUMERO": Role.META,
    "SOLUTION": Role.META,
    # Les liens
    "LIENS": Role.LINK,
    "LIEN": Role.LINK,
}

_TRANSPARENT = {
    # Les deux seules balises de mise en forme du corpus juri
    "p": "\n\n",
    "br": "\n",
}

_COMMON_RENAMES = {
    "ANCIEN_ID": "ancien_id",
    "ORIGINE": "origine",
    "URL": "url",
    "DATE_DEC": "date_decision",
    "JURIDICTION": "juridiction",
    "NUMERO": "numero",
    "SOLUTION": "solution",
    "ECLI": "ecli",
}


def _table(
    roles: dict[str, Role], renames: dict[str, str], root: str, prefix: str
) -> RoleTable:
    """Le socle commun plus les spécificités d'une racine, fusionnés à l'import pour que
    les trois tables ne divergent pas."""
    return RoleTable(
        roots=(root,),
        roles={root: Role.META, **_COMMON_ROLES, **roles},
        content_blocks=("BLOC_TEXTUEL",),
        text_holders=("CONTENU",),
        title_tags=("TITRE",),
        identifier_tag="ID",
        document_types={prefix: DocumentType.DECISION},
        meta_containers=("META",),
        meta_renames={**_COMMON_RENAMES, **renames},
        # Un arrêt est rendu une fois
        version_tags=frozenset(),
        transparent=_TRANSPARENT,
        links=JURI_LINK_TABLE,
        link_tags=("LIEN",),
        link_containers=(),
        structural_link_tags=(),
        ancestor_containers=(),
        ancestor_tags=(),
    )


# ── TEXTE_JURI_JUDI — CAPP, CASS, INCA ─────────────────────────────────────────

JURI_JUDI_ROLE_TABLE = replace(
    _table(
        root="TEXTE_JURI_JUDI",
        prefix="JURITEXT",
        roles={
            "META_JURI_JUDI": Role.META,
            "FORMATION": Role.META,
            "FORM_DEC_ATT": Role.META,
            "DATE_DEC_ATT": Role.META,
            "SIEGE_APPEL": Role.META,
            "JURI_PREM": Role.META,
            "LIEU_PREM": Role.META,
            "DEMANDEUR": Role.META,
            "DEFENDEUR": Role.META,
            "PRESIDENT": Role.META,
            "AVOCAT_GL": Role.META,
            "AVOCATS": Role.META,
            "RAPPORTEUR": Role.META,
            "NUMEROS_AFFAIRES": Role.META,
            "NUMERO_AFFAIRE": Role.META,
            "PUBLI_BULL": Role.META,
            # Hors `content_blocks` : le sommaire commente la décision, il polluerait
            # l'embedding
            "SOMMAIRE": Role.BODY,
            "SCT": Role.BODY,
            "ANA": Role.BODY,
            "CITATION_JP": Role.BODY,
        },
        renames={
            "FORMATION": "formation",
            "PRESIDENT": "president",
            "AVOCATS": "avocats",
            "RAPPORTEUR": "rapporteur",
            "NUMERO_AFFAIRE": "numero_affaire",
            "DATE_DEC_ATT": "date_decision_attaquee",
            "FORM_DEC_ATT": "formation_decision_attaquee",
            "SIEGE_APPEL": "siege_appel",
        },
    ),
    # Des décisions CASS portent plusieurs NUMERO_AFFAIRE distincts
    list_keys=frozenset({"numero_affaire"}),
)
"""Le judiciaire : cours d'appel (CAPP), Cour de cassation (CASS), inédits (INCA)."""


# ── TEXTE_JURI_ADMIN — JADE ────────────────────────────────────────────────────

JURI_ADMIN_ROLE_TABLE = replace(
    _table(
        root="TEXTE_JURI_ADMIN",
        prefix="CETATEXT",
        roles={
            "META_JURI_ADMIN": Role.META,
            "FORMATION": Role.META,
            "TYPE_REC": Role.META,
            "PUBLI_RECUEIL": Role.META,
            "DEMANDEUR": Role.META,
            "DEFENDEUR": Role.META,
            "PRESIDENT": Role.META,
            "AVOCATS": Role.META,
            "RAPPORTEUR": Role.META,
            # Devenu « rapporteur public » en 2009 ; la balise a gardé son nom
            "COMMISSAIRE_GVT": Role.META,
            "SOMMAIRE": Role.BODY,
            "SCT": Role.BODY,
            "ANA": Role.BODY,
            "CITATION_JP": Role.BODY,
        },
        renames={
            "FORMATION": "formation",
            "PRESIDENT": "president",
            "AVOCATS": "avocats",
            "RAPPORTEUR": "rapporteur",
            "TYPE_REC": "type_recours",
            "PUBLI_RECUEIL": "publication_recueil",
            "COMMISSAIRE_GVT": "rapporteur_public",
        },
    ),
    # JADE écrit `Texte` dans NATURE pour toutes ses décisions
    uninformative_natures=frozenset({"TEXTE"}),
)
"""L'administratif : Conseil d'État, cours administratives d'appel, tribunaux (JADE)."""


# ── TEXTE_JURI_CONSTIT — CONSTIT ───────────────────────────────────────────────

JURI_CONSTIT_ROLE_TABLE = _table(
    root="TEXTE_JURI_CONSTIT",
    prefix="CONSTEXT",
    roles={
        "META_JURI_CONSTIT": Role.META,
        "NOR": Role.META,
        "NATURE_QUALIFIEE": Role.META,
        "TITRE_JO": Role.META,
        "URL_CC": Role.META,
        # La loi déférée : décrite par ses attributs, sans `<LIEN>` ni `typelien`. En
        # faire une arête serait une décision à prendre, pas un effet de bord.
        "LOI_DEF": Role.META,
        # Les mémoires des parties : des pièces du dossier, pas des commentaires
        "SAISINES": Role.BODY,
        "OBSERVATIONS": Role.BODY,
    },
    renames={
        "NOR": "nor",
        "NATURE_QUALIFIEE": "nature_qualifiee",
        "TITRE_JO": "titre_jo",
        "URL_CC": "url_conseil_constitutionnel",
    },
)
"""Le Conseil constitutionnel (CONSTIT)."""


ROLE_TABLE_BY_ROOT = {
    "TEXTE_JURI_JUDI": JURI_JUDI_ROLE_TABLE,
    "TEXTE_JURI_ADMIN": JURI_ADMIN_ROLE_TABLE,
    "TEXTE_JURI_CONSTIT": JURI_CONSTIT_ROLE_TABLE,
}
"""La racine XML choisit la table de rôles."""
