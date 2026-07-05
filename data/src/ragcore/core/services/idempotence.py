"""Service d'idempotence — détermine l'opération sur un document.

Après suppression du content_hash, la logique est radicalement simplifiée :
- Si manifest_entry est None → INSERT (premier run)
- Sinon → UPDATE (toujours, peu importe le contenu)

Pas de SKIP ni de REPLACE.
"""

from ..models.enums import Operation
from ..models.manifest import ManifestEntry


def determine_operation(
    manifest_entry: ManifestEntry | None,
) -> Operation:
    """Détermine l'opération à effectuer sur un document.

    Args:
        manifest_entry: Dernière entrée du manifest pour ce document, ou None si absent.

    Returns:
        Operation.INSERT si aucune entrée précédente.
        Operation.UPDATE si le document a déjà été traité.
    """
    if manifest_entry is None:
        return Operation.INSERT
    return Operation.UPDATE
