"""Vocabulaire suggéré pour les raisons d'exclusion dans le manifest.

Ces constantes encouragent la cohérence, mais le champ 'reason' reste libre (string).
"""

# Raisons d'exclusion liées à l'identifiant ELI (LEGI)
REASON_NO_ELI = "no_eli"
REASON_INVALID_ELI = "invalid_eli_format"

# Raisons d'exclusion générales
REASON_PARSE_ERROR = "parse_error"
REASON_VALIDATION_ERROR = "validation_error"
REASON_MISSING_CONTENT = "missing_content"
