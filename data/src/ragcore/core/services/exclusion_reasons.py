"""Les raisons d'exclusion (``reason`` des événements de rejet) : une raison qui n'est
pas ici n'existe pas.
"""

# Rejet au parse : lecture impossible
REASON_PARSE_ERROR = "parse_error"

# Rejets au parse : document lisible mais irrecevable, une raison par règle métier
REASON_IDENTIFIER_MISSING = "identifier_missing"
REASON_IDENTIFIER_MALFORMED = "identifier_malformed"
REASON_UNDECLARED_PREFIX = "undeclared_prefix"
# Les facettes ne s'ordonnent que par `table.roots` (ADR-025) : sans ordre, pas de
# document.
REASON_FACET_ROOT_DUPLICATED = "facet_root_duplicated"
REASON_FACET_ROOT_UNDECLARED = "facet_root_undeclared"
# Une clé renommée, non déclarée `list`, a reçu plusieurs valeurs distinctes (ADR-025)
REASON_COLLISION = "collision"

# Un fichier livré qui n'est pas un document (LEGI : les `versions.xml`, un ID nu). Le
# connecteur l'écarte avant le parser, pour ne pas noyer les vrais rejets, et le compte.
REASON_EXPORT_ARTIFACT = "export_artifact"

# XML illisible (tronqué, encodage cassé) : pas d'arbre du tout. Distinct de
# `parse_error`, où l'arbre existait : les confondre masquerait une corruption de la
# source derrière un bug supposé du parser.
REASON_UNREADABLE = "unreadable"

# Un fichier dont l'`<ID>` n'est pas son nom (ADR-034 §1) : la clé du flux est le nom, et
# un document émis sous une autre clé que son identifiant pourrait être traité par deux
# workers. Couvre aussi un `versions.xml` qui n'est pas un artefact.
REASON_ID_MISMATCH = "id_mismatch"
