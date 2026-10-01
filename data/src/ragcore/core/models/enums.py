from enum import StrEnum


class SourceName(StrEnum):
    LEGI = "legi"
    JORF = "jorf"
    UPLOAD = "upload"

    # Jurisprudence : une valeur par base.
    CAPP = "capp"  # cours d'appel
    CASS = "cass"  # Cour de cassation
    INCA = "inca"  # inédits Cour de cassation
    JADE = "jade"  # juridictions administratives
    CONSTIT = "constit"  # Conseil constitutionnel


class DocumentType(StrEnum):
    """La forme d'un document, déduite du préfixe de son identifiant.

    Un ensemble FERMÉ, écrit à l'identique dans Mongo, Qdrant et Neo4j. La nature
    juridique (``LOI``, ``ARRET``, ``QPC``…) n'en est pas : c'est ``ParsedDocument.nature``.
    """

    ARTICLE = "article"
    SECTION = "section"
    TEXTE = "texte"
    DECISION = "decision"


class TargetStore(StrEnum):
    MONGO = "mongo"
    NEO4J = "neo4j"
    QDRANT = "qdrant"


# ── `RelationType` a été supprimé. Ce n'est pas un oubli. ──────────────────────────
#
# C'était un `StrEnum` de six verbes. Un `typelien` hors de ces six ne pouvait pas
# devenir une arête : la traduction rendait `None`, l'extracteur faisait `return None`,
# et la relation était *déclarée perdue* au lieu d'être *écrite*.
#
# Un enum de verbes suppose que le domaine connaît d'avance tout ce que six sources
# hétérogènes vont dire. Ce pari est perdu d'avance, et il se paie en arêtes qui
# n'existent pas.
#
# Le verbe est désormais une CHAÎNE VALIDÉE (`core/models/verbs.py` pour la règle de
# forme, `core/links/vocabulary.py` pour les verbes que le domaine sait nommer). Un mot
# de source non traduit entre dans le graphe SOUS SON NOM BRUT et remonte dans
# `unknowns` : le graphe porte une arête vraie et un aveu, jamais un vide.
