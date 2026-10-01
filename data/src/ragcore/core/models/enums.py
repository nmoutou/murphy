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
    """La forme d'un document, déduite du préfixe de son identifiant, écrite à
    l'identique dans Mongo, Qdrant et Neo4j. La nature juridique (``LOI``, ``QPC``…)
    est ailleurs : ``ParsedDocument.nature``.
    """

    ARTICLE = "article"
    SECTION = "section"
    TEXTE = "texte"
    DECISION = "decision"


class TargetStore(StrEnum):
    MONGO = "mongo"
    NEO4J = "neo4j"
    QDRANT = "qdrant"
