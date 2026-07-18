"""Le verbe d'une arête — et la traduction qui ne jette jamais rien.

**L'enum fermé est mort, et voici pourquoi.** ``RelationType`` était un ``StrEnum`` de
six membres. Un ``typelien`` hors de ces six ne pouvait littéralement pas devenir une
arête : ``TYPELIEN_TO_RELATION.get(...)`` rendait ``None``, et l'extracteur faisait
``return None``. L'arête était **déclarée perdue** (``unknowns``) au lieu d'être
**écrite**. Le fil rouge ne faisait que la moitié du contrat : il nommait le trou, il
ne le bouchait pas.

Un enum de verbes est un pari intenable : il suppose que le domaine connaît, à
l'avance, tout ce que six sources hétérogènes vont dire. Ce pari est perdu d'avance —
et il se paie en arêtes qui n'existent pas.

**Ce qui le remplace.** Le verbe est une chaîne validée. Le domaine nomme les verbes
qu'il *sait* interpréter (ci-dessous) ; une source qui en déclare un autre le fait
entrer **sous son nom brut**, et le fait est signalé. Le graphe contient alors une
arête vraie et un aveu — jamais un vide.

**Ce n'est pas un renoncement à la sémantique, c'est un ordre d'arrivée.** Le mot brut
entre d'abord, il est visible dans le ``RunSummary``, et le jour où le domaine décide
de ce que ``CODIFICATION`` veut dire, il gagne un verbe canonique et la table de la
source le traduit. L'inverse — le rendre traduisible avant de l'avoir vu — était
précisément l'erreur.

**Ce que ça coûte, dit franchement.** Le graphe porte du vocabulaire de source à côté
du vocabulaire du domaine. Le voisinage du serving devra donc filtrer sur les verbes
qu'il connaît plutôt que de traverser aveuglément. C'est le prix, et il est plus faible
que celui d'une arête inexistante : on peut ignorer un verbe qu'on ne comprend pas, on
ne peut pas parcourir une arête qui n'a jamais été écrite.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import NewType

from ..models.verbs import VERB_PATTERN, normalize_verb

__all__ = [
    "ABROGATES",
    "CANONICAL_VERBS",
    "CITES",
    "CONTAINS",
    "CREATES",
    "MODIFIES",
    "REFERENCES",
    "SUCCEEDED_BY",
    "RelationVerb",
    "TranslationTable",
    "is_valid_verb",
    "translate",
    "verb",
]

RelationVerb = NewType("RelationVerb", str)
"""Le verbe d'une arête. Une chaîne — pas un membre d'enum.

Toujours nommé **du point de vue de la source** de l'arête : c'est ce qui fait de
``MODIFIE`` et ``MODIFICATION`` le même verbe, vu de ses deux bouts. L'attribut ``sens``
dit de quel bout on regarde ; le verbe, lui, ne change pas.

La règle de forme (``VERB_PATTERN``) est définie dans ``core/models/verbs`` et pas ici :
les modèles en ont besoin pour valider leurs champs, et ils ne peuvent pas importer
``core/links`` sans faire un cycle. **Une seule vérité, deux portes d'entrée.**
"""


# ── Ce que le domaine sait nommer ───────────────────────────────────────────────
#
# Des CONSTANTES, pas un enum : la différence n'est pas cosmétique. Un enum est
# *fermé* — sa valeur est soit membre, soit invalide. Ces constantes sont des noms
# *privilégiés* dans un espace ouvert : elles disent « voici les verbes dont le domaine
# connaît la sémantique », sans prétendre qu'aucun autre ne puisse exister.

CITES = RelationVerb("cites")
MODIFIES = RelationVerb("modifies")
ABROGATES = RelationVerb("abrogates")
CREATES = RelationVerb("creates")

CONTAINS = RelationVerb("contains")
"""Contenance structurelle : un texte contient ses sections, une section ses articles.

Le SEUL verbe transitif par nature — donc le seul réductible
(cf. ``core/services/relation_reduction``). Son orientation ne vient jamais d'un
attribut ``sens`` : elle est connue par construction.
"""

REFERENCES = RelationVerb("references")
"""Le renvoi qualifié : la source déclare un lien dont le verbe précis n'a pas (encore)
de sémantique propre dans le domaine, mais qu'on a décidé de ranger ici **sciemment**.

À ne pas confondre avec le verbe brut d'un typelien inconnu. ``REFERENCES`` est un choix
inscrit dans une table de traduction ; le nom brut est ce qui se passe quand il n'y a
pas de choix. Le premier dit « je sais, et je range ici » ; le second dit « je ne sais
pas, et je le montre ».
"""

SUCCEEDED_BY = RelationVerb("succeeded_by")
"""L'axe temporel : ``(v1)-[:succeeded_by]->(v2)``, dans le sens de l'écoulement du temps.

Ni une contenance (le réduire détruirait la ligne de vie), ni une citation : chaque
``<LIEN_ART>`` d'un bloc ``<VERSIONS>`` désigne une version datée du MÊME article. Le
graphe ne porte PAS le produit cartésien de ces liens (``has_version``, remplacé le jour
même de sa naissance — 2 760 arêtes « dans tous les sens ») : il porte la **chaîne** —
chaque version pointe sa suivante, l'auto-référence servant d'ancre pour localiser le
document dans sa propre liste. Une version mort-née (``etat`` en ``_MORT_NE`` : jamais
entrée en vigueur) est HORS chaîne, accrochée en branche latérale à la version en vigueur
au moment de l'avortement — l'``etat`` sur l'arête permet de l'écarter d'une requête.
"""

CANONICAL_VERBS: frozenset[RelationVerb] = frozenset(
    {CITES, MODIFIES, ABROGATES, CREATES, CONTAINS, REFERENCES, SUCCEEDED_BY}
)
"""Les verbes dont le domaine connaît la sémantique — figés par un cliquet.

**Cet ensemble n'est PAS une validation.** Un verbe hors de cet ensemble est parfaitement
légitime dans le graphe : c'est un mot de source non encore traduit. Cet ensemble sert à
deux choses, et à deux choses seulement : dire au serving quels verbes il peut
interpréter, et donner au cliquet de normalisation quelque chose à figer (ces valeurs
sont écrites en base — les renommer rendrait illisible ce qui est déjà stocké).
"""


TranslationTable = Mapping[str, RelationVerb]
"""Le vocabulaire d'UNE source vers celui du domaine.

Elle vit dans ``sources/<nom>/`` — jamais ici. Le domaine ne doit pas savoir que LEGI
dit ``CODIFICATION`` : le jour où il le sait, le vocabulaire d'un fournisseur a colonisé
le langage commun.
"""


def verb(raw: str) -> RelationVerb:
    """Fabrique un verbe à partir d'une chaîne — en la validant.

    Lève ``ValueError`` si la chaîne ne peut pas être un type d'arête Neo4j. C'est le
    seul point de passage : ailleurs dans le code, un ``RelationVerb`` est *par
    construction* sûr à écrire dans une requête.
    """
    return RelationVerb(normalize_verb(raw))


def is_valid_verb(raw: str) -> bool:
    """Vrai si ``raw`` peut devenir un verbe — sans lever."""
    return bool(VERB_PATTERN.match(raw.strip().lower()))


def translate(table: TranslationTable, raw: str) -> tuple[RelationVerb | None, bool]:
    """Traduit le mot d'une source en verbe du domaine — ou le laisse entrer brut.

    Rend ``(verbe, connu)``.

    - ``connu=True``  : la table a traduit. Le verbe est un des ``CANONICAL_VERBS``.
    - ``connu=False`` : la table ne connaît pas ce mot. Le verbe est **le mot brut**,
      normalisé en minuscules. **L'arête existe quand même** — c'est tout l'objet de
      cette fonction, et la différence avec le ``return None`` qu'elle remplace.
    - ``(None, False)`` : le mot ne peut pas *être* un verbe (vide, ou caractères
      interdits). Là seulement, il n'y a pas d'arête — parce qu'il n'y a rien à écrire,
      pas parce qu'on a renoncé.

    L'appelant tient une ``WorkerTelemetry`` : c'est LUI qui déclare l'inconnu
    (``record_unknown``) quand ``connu`` est faux. Cette fonction ne connaît pas la
    télémétrie, et c'est ce qui la garde pure — elle est appelée dans le worker, pas
    dans le hook.
    """
    known = table.get(raw)
    if known is not None:
        return known, True

    if not is_valid_verb(raw):
        # Un `typelien` vide ou biscornu n'est pas un vocabulaire à apprendre : il n'y a
        # aucun mot dessous. On ne fabrique pas un type d'arête à partir de rien.
        return None, False

    # Le mot entre dans le graphe TEL QUEL. Il est faux de dire qu'on ne l'a pas compris
    # et de le jeter : on ne l'a pas compris, et on le montre — dans le graphe, et dans
    # le bilan du run.
    return verb(raw), False
