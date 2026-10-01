"""Le connecteur de jurisprudence : un fichier, un document, sans interprétation.

Contrairement à LEGI, ni fusion de facettes (chaque ``<ID>`` apparaît dans un seul
fichier) ni artefact d'export. Une classe pour les cinq bases, qui ne diffèrent que par
leur racine, affaire du parser.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.services.exclusion_reasons import REASON_UNREADABLE
from ragcore.sources.generic import locate_id, read_root, to_tree

__all__ = ["JuriFileConnector"]


class JuriFileConnector:
    """Instancié une fois par base : la base est un paramètre, pas un type."""

    def __init__(self, root: Path | str, source: SourceName) -> None:
        self._root = Path(root)
        self._source = source
        self.skipped: dict[str, int] = {}
        """Seuls les fichiers illisibles : la juri n'a pas d'artefact d'export."""

    @property
    def source_name(self) -> SourceName:
        return self._source

    async def fetch_all(self) -> AsyncIterator[RawDocument]:
        """Sans regroupement, donc au fil de l'eau : rien n'est gardé en mémoire."""
        self.skipped = {}

        for path in sorted(self._root.rglob("*.xml")):
            root = read_root(path)
            if root is None:
                self._skip(REASON_UNREADABLE)
                continue

            yield RawDocument(
                source=self._source,
                source_document_id=locate_id(root) or str(path),
                payload={
                    # Une liste, même d'une facette : le parser ne distingue pas les sources
                    "content": [to_tree(root)],
                    "files": [str(path)],
                },
                fetched_at=datetime.now(UTC),
            )

    def _skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1
