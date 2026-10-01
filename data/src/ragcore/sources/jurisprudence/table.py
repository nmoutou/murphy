"""La jurisprudence — **trois tables, cinq sources, zéro parser**.

C'est ici que §3 se vérifie ou se dément : *« une source nouvelle = une table, pas un
second parser »*. Ce fichier ne contient **aucune logique** — pas une boucle, pas une
condition. Le parser générique fait tout le travail ; la juri n'apporte que du vocabulaire.

**Cinq sources, trois tables — et pas cinq.** Le corpus déclare trois racines seulement :

    TEXTE_JURI_JUDI     CAPP, CASS, INCA   (judiciaire : cours d'appel, Cassation)
    TEXTE_JURI_ADMIN    JADE               (administratif : Conseil d'État, CAA, TA)
    TEXTE_JURI_CONSTIT  CONSTIT            (Conseil constitutionnel)

CAPP, CASS et INCA **partagent la même table**, à l'identique. Ce n'est pas une
simplification de notre part : c'est la structure que DILA publie. Une table par *forme
de document*, pas une par *base* — la base n'est qu'un champ.

**La structure est celle de LEGI.** ``META/META_COMMUN/{ID, ORIGINE, URL, NATURE}`` : les
mêmes balises, au même endroit. ``TEXTE/BLOC_TEXTUEL/CONTENU`` pour le corps.
``LIENS/LIEN`` avec ``@sens`` et ``@typelien``. Ce qui change tient dans ``META_SPEC`` —
les métadonnées propres au juridictionnel (formation, avocats, solution…).

**Ce que la juri n'a PAS, et qui se lit dans les tables :**

- **aucun rôle ``VERSION``** — pas de ``date_debut``/``date_fin``/``etat``. Un arrêt est
  rendu une fois ; il n'a pas de versions successives comme un article de code. Le rôle
  existe (§3 : « version = stratégie optionnelle, no-op si absente »), aucune balise n'y
  est mappée, le handler ne s'active pas. C'était prévu ; c'est vérifié.
- **aucune structure** — pas de ``<CONTEXTE>``, pas de ``<STRUCTURE_TA>``. Un arrêt ne
  contient pas d'autres arrêts. Là où LEGI déclare un arbre, la juri est plate.
- **aucune cible de lien identifiée** — cf. ``vocabulary.py`` : c'est LA découverte du lot.
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
# Ce que TOUTE décision de justice porte, quelle que soit la juridiction. C'est très
# exactement le `META_COMMUN` de LEGI : la structure DILA est unique.

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
    # Ce que TOUTE décision porte
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
    # La juri n'utilise que deux balises de mise en forme (mesuré). Son corps est du texte
    # brut avec des sauts — pas le HTML riche des articles de LEGI.
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
    """Assemble une table juri à partir du socle commun et de ses spécificités.

    Une **fonction de composition**, pas de la logique : elle ne décide rien, elle
    fusionne deux dictionnaires. Le parser générique ne l'appelle jamais — elle ne tourne
    qu'à l'import, pour éviter de recopier trois fois vingt lignes identiques. Recopier
    aurait laissé les trois tables diverger au premier correctif.
    """
    return RoleTable(
        roots=frozenset({root}),
        roles={root: Role.META, **_COMMON_ROLES, **roles},
        content_blocks=("BLOC_TEXTUEL",),
        text_holders=("CONTENU",),
        title_tags=("TITRE",),
        identifier_tag="ID",
        # Un seul type pour les trois ordres de juridiction : la source les distingue.
        document_types={prefix: DocumentType.DECISION},
        meta_containers=("META",),
        meta_renames={**_COMMON_RENAMES, **renames},
        # AUCUNE balise de version : un arrêt est rendu une fois. Le rôle existe, il ne
        # s'active pas — exactement le « no-op si absente » de §3.
        version_tags=frozenset(),
        transparent=_TRANSPARENT,
        links=JURI_LINK_TABLE,
        link_tags=("LIEN",),
        # Aucun lien structurel, aucun ancêtre : un arrêt ne contient pas d'arrêts.
        link_containers=(),
        structural_link_tags=(),
        ancestor_containers=(),
        ancestor_tags=(),
    )


# ── TEXTE_JURI_JUDI — CAPP, CASS, INCA ─────────────────────────────────────────

JURI_JUDI_ROLE_TABLE = _table(
    root="TEXTE_JURI_JUDI",
    prefix="JURITEXT",
    roles={
        "META_JURI_JUDI": Role.META,
        # La procédure : qui a jugé, qui plaidait, contre qui.
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
        # Le sommaire : l'analyse doctrinale de l'arrêt. C'est du TEXTE, et du bon — mais
        # il n'est PAS dans `content_blocks` : c'est un commentaire *sur* la décision, pas
        # la décision. Le fondre dans le corps polluerait l'embedding avec de la glose.
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
)
"""Le judiciaire : cours d'appel (CAPP), Cour de cassation (CASS), inédits (INCA).

**Trois bases, une table.** Elles publient exactement la même structure — c'est DILA qui
en décide, pas nous. La base d'origine est un simple champ (``SourceName``), pas un type.
"""


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
            # Le commissaire du gouvernement — devenu « rapporteur public » en 2009. Le nom de
            # la balise, lui, n'a pas suivi : la source garde son vocabulaire d'origine.
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
    # JADE écrit `Texte` dans NATURE, pour toutes ses décisions (mesuré).
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
        # La loi déférée au Conseil : ses attributs (@date, @nor, @num) la DÉCRIVENT, mais
        # ce n'est pas une balise <LIEN> et elle n'a pas de `typelien`. La traiter comme un
        # lien demanderait une règle rien que pour elle — on la range en métadonnée, et le
        # jour où le graphe doit porter « cette décision contrôle cette loi », ce sera une
        # décision prise, pas un effet de bord.
        "LOI_DEF": Role.META,
        # Les saisines et observations : les mémoires des parties. Du texte, versé au
        # corps — contrairement au sommaire du judiciaire, ce ne sont pas des commentaires
        # a posteriori mais des pièces du dossier.
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
"""**Le doc_type ne fait que choisir la table** (§3, littéralement).

La racine XML sélectionne la table de rôles qui s'applique. Ce n'est pas du typage métier
réintroduit par la bande : il n'y a ni classe ``Arrêt`` ni classe ``Décision`` — il y a
trois données, et un dictionnaire pour les choisir.
"""
