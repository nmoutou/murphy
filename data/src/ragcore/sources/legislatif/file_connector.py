"""Le connecteur de fichiers LEGI : le connecteur générique, plus les artefacts
d'export.

Les ``versions.xml`` partagent tous la clé ``versions`` : la passe 1 les met à part, et
ils sont lus un par un après les documents. Un ``<VERSIONS>`` ou un ``<ID>`` nu est un
artefact, écarté et compté pour ne pas noyer les vrais rejets. Tout autre
``versions.xml`` est rejeté : son ``<ID>`` n'est pas son nom.
"""

from collections.abc import Iterator
from pathlib import Path

from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.inventory import SourceInventory
from ragcore.core.services.exclusion_reasons import REASON_EXPORT_ARTIFACT
from ragcore.sources.generic import KeyedFileConnector, locate_id

__all__ = ["LegiFileConnector"]

_EXPORT_ARTIFACT_KEY = "versions"
_EXPORT_ARTIFACT_ROOTS = frozenset({"VERSIONS", "ID"})
"""Les deux formes de l'artefact d'export : ``<VERSIONS>``, ou une ligne réduite à
``<ID>``. Ni contenu, ni titre, ni relation."""


class LegiFileConnector:
    source_name = SourceName.LEGI

    def __init__(self, root: Path | str) -> None:
        self._files = KeyedFileConnector(
            root, SourceName.LEGI, set_aside=(_EXPORT_ARTIFACT_KEY,)
        )

    @property
    def skipped(self) -> dict[str, int]:
        return self._files.skipped

    def discover(self) -> dict[SourceName, SourceInventory]:
        return self._files.discover()

    def fetch_all(self) -> Iterator[RawDocument]:
        yield from self._files.fetch_all()
        for path in self._files.set_aside_paths:
            self._screen_export_candidate(path)

    def _screen_export_candidate(self, path: str) -> None:
        root = self._files.read_counted(path)
        if root is None:
            return
        if root.tag in _EXPORT_ARTIFACT_ROOTS:
            self._files.skip(REASON_EXPORT_ARTIFACT)
            return
        self._files.reject_id_mismatch(path, locate_id(root), _EXPORT_ARTIFACT_KEY)
