"""Vocabulaire des raisons d'exclusion (``reason`` des événements de rejet).

Source de vérité : les sites d'émission importent ces constantes plutôt que
d'écrire les chaînes. Une raison qui n'est pas ici n'existe pas.
"""

# Rejets au parse : lecture impossible (`parse_error`) ou document lisible mais
# irrecevable, p. ex. identifiant absent ou mal formé (`validation_error`).
REASON_PARSE_ERROR = "parse_error"
REASON_VALIDATION_ERROR = "validation_error"

# Artefact d'export : un fichier que la source livre mais qui n'est pas un document
# (LEGI : les 1637 `versions.xml`, qui ne contiennent qu'un ID nu). Le connecteur les
# écarte AVANT le parser — les lui passer produirait 1637 rejets qui noieraient les
# vrais sous du bruit connu. Écarté n'est pas silencieux : le connecteur les compte.
REASON_EXPORT_ARTIFACT = "export_artifact"

# XML illisible : le fichier existe mais ne parse pas (tronqué, encodage cassé). Le
# connecteur ne peut rien en transcrire — il n'y a pas d'arbre. C'est une exclusion de
# LECTURE, distincte du `parse_error` qui est un échec d'INTERPRÉTATION : là, l'arbre
# existait et le parser n'a pas su le lire. Les confondre masquerait une corruption de la
# source derrière un bug supposé du parser.
REASON_UNREADABLE = "unreadable"
