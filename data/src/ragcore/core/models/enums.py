from enum import StrEnum


class SourceName(StrEnum):
    LEGI = "legi"
    JORF = "jorf"
    UPLOAD = "upload"

    # Jurisprudence : une valeur par base.
    CAPP = "capp"          # cours d'appel
    CASS = "cass"          # Cour de cassation
    INCA = "inca"          # inédits Cour de cassation
    JADE = "jade"          # juridictions administratives
    CONSTIT = "constit"    # Conseil constitutionnel


class Operation(StrEnum):
    """Opération effectuée sur un document lors du manifest."""

    INSERT = "insert"       # première ingestion (identifier inconnu du manifest)
    UPDATE = "update"       # ré-ingestion (identifier déjà connu)
    DELETE = "delete"       # suppression
    EXCLUDED = "excluded"   # rejet de validation, jamais ingéré


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
