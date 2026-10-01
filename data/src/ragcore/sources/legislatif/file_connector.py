"""Le connecteur de fichiers LEGI : il transcrit sans interpréter.

Il prend deux décisions, sans regarder le contenu :

1. Il écarte et compte les artefacts d'export (les ``versions.xml``, un ID nu), qui
   noieraient les vrais rejets.
2. Il fusionne les deux facettes d'un texte : ``TEXTE_VERSION`` porte le titre et les
   métadonnées, ``TEXTELR`` la structure. Émises séparément, l'une écraserait l'autre,
   et les textes finiraient sans titre.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.services.exclusion_reasons import (
    REASON_EXPORT_ARTIFACT,
    REASON_UNREADABLE,
)
from ragcore.sources.generic import locate_id, read_root, to_tree

__all__ = ["LegiFileConnector"]

_EXPORT_ARTIFACT_NAME = "versions.xml"
_EXPORT_ARTIFACT_ROOTS = frozenset({"VERSIONS", "ID"})
"""Les deux formes de l'artefact d'export : ``<VERSIONS>``, ou une ligne réduite à
``<ID>``. Ni contenu, ni titre, ni relation."""


class LegiFileConnector:
    source_name = SourceName.LEGI

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)
        self.skipped: dict[str, int] = {}
        """Ce que le connecteur a écarté, par raison."""

    async def fetch_all(self) -> AsyncIterator[RawDocument]:
        """Un document par identifiant. La fusion impose de lire tous les arbres avant
        d'émettre : seuls les arbres sont gardés en mémoire.
        """
        self.skipped = {}
        by_identifier: dict[str, list[tuple[Path, dict[str, Any]]]] = {}

        for path in sorted(self._root.rglob("*.xml")):
            root = read_root(path)
            if root is None:
                self._skip(REASON_UNREADABLE)
                continue

            if self._is_export_artifact(path, root):
                self._skip(REASON_EXPORT_ARTIFACT)
                continue

            tree = to_tree(root)
            by_identifier.setdefault(locate_id(root) or str(path), []).append(
                (path, tree)
            )

        for source_document_id, facets in by_identifier.items():
            yield RawDocument(
                source=SourceName.LEGI,
                source_document_id=source_document_id,
                payload={
                    # Une liste, même d'une facette : fusion et cas simple, même chemin
                    "content": [tree for _, tree in facets],
                    "files": [str(path) for path, _ in facets],
                },
                fetched_at=datetime.now(UTC),
            )

    def _is_export_artifact(self, path: Path, root: ET.Element) -> bool:
        """Le nom et la racine, jamais le nom seul : un ``versions.xml`` de racine
        ``<ARTICLE>`` est un document."""
        return path.name == _EXPORT_ARTIFACT_NAME and root.tag in _EXPORT_ARTIFACT_ROOTS

    def _skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1
