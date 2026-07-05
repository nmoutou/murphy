from enum import StrEnum


class SourceName(StrEnum):
    LEGI = "legi"
    JORF = "jorf"
    JADE = "jade"
    UPLOAD = "upload"


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


class RelationType(StrEnum):
    CITES = "cites"
    MODIFIES = "modifies"
    ABROGATES = "abrogates"
    REFERENCES = "references"
