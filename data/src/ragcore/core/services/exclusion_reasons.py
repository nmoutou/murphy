"""Les raisons d'exclusion (``reason`` des événements de rejet) : une raison qui n'est
pas ici n'existe pas.
"""

# Rejets au parse : lecture impossible, ou document lisible mais irrecevable
REASON_PARSE_ERROR = "parse_error"
REASON_VALIDATION_ERROR = "validation_error"
# Une clé renommée, non déclarée `list`, a reçu plusieurs valeurs distinctes (ADR-025) :
# un refus métier, nommé à part pour se lire au bilan.
REASON_COLLISION = "collision"

# Un fichier livré qui n'est pas un document (LEGI : les `versions.xml`, un ID nu). Le
# connecteur l'écarte avant le parser, pour ne pas noyer les vrais rejets, et le compte.
REASON_EXPORT_ARTIFACT = "export_artifact"

# XML illisible (tronqué, encodage cassé) : pas d'arbre du tout. Distinct de
# `parse_error`, où l'arbre existait : les confondre masquerait une corruption de la
# source derrière un bug supposé du parser.
REASON_UNREADABLE = "unreadable"
