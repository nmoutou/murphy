"""Le connecteur d'une source de fichiers XML : il transcrit sans interpréter le
contenu.

La clé d'un document est le nom de son fichier sans extension, qui doit être son
``<ID>`` (ADR-034 §1). Elle se lit sans ouvrir le fichier : la passe 1 indexe toute
l'arborescence, la passe 2 lit les facettes d'une clé au moment de l'émettre. La fusion
reste globale : les copies d'une même racine vivent dans deux dossiers, et seule la
plus récente fait foi (``copy_arbitration``).
"""

from __future__ import annotations

import logging
from collections.abc import Collection, Iterator
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from ragcore.core.models.collision_record import CollisionRecord
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.inventory import FULL_RATIO, SourceInventory
from ragcore.core.models.problems import FileProblem, MismatchedFile, UnreadableFile
from ragcore.core.services.exclusion_reasons import (
    REASON_ID_MISMATCH,
    REASON_SUPERSEDED,
    REASON_UNREADABLE,
)
from ragcore.core.services.key_sampling import select_keys

from .copy_arbitration import Facet, arbitrate
from .xml_tree import locate_id, read_root, to_tree

__all__ = ["KeyedFileConnector"]

logger = logging.getLogger(__name__)

_XML_GLOB = "*.xml"


class KeyedFileConnector:
    """Un document par clé, de une ou plusieurs facettes.

    ``ingestion_ratio`` (ADR-034 §9) choisit les clés émises avant toute lecture : un
    document écarté ne coûte rien. ``set_aside`` nomme des clés que la passe 1 met à
    part, sans les émettre ni les échantillonner : celles d'un nom de fichier partagé
    par des fichiers sans rapport (LEGI : ``versions``). L'appelant les traite
    (``set_aside_paths``).
    """

    def __init__(
        self,
        root: Path | str,
        source: SourceName,
        ingestion_ratio: float = FULL_RATIO,
        set_aside: Collection[str] = (),
    ) -> None:
        self._root = Path(root)
        self._source = source
        self._ratio = ingestion_ratio
        self._set_aside_keys = frozenset(set_aside)
        self._index: dict[str, list[str]] | None = None
        self.set_aside_paths: list[str] = []
        self.skipped: dict[str, int] = {}
        self.collisions: list[CollisionRecord] = []
        self.problems: list[FileProblem] = []

    @property
    def source_name(self) -> SourceName:
        return self._source

    def discover(self) -> dict[SourceName, SourceInventory]:
        """Les chemins sont gardés en chaînes : un ``Path`` pèse plusieurs fois plus,
        et l'index tient tout le stock."""
        self.skipped = {}
        self.collisions = []
        self.problems = []
        index: dict[str, list[str]] = {}
        for path in self._root.rglob(_XML_GLOB):
            index.setdefault(path.stem, []).append(str(path))
        self.set_aside_paths = sorted(
            path for key in self._set_aside_keys for path in index.pop(key, [])
        )
        self._index = self._sample(index)
        return {
            self._source: SourceInventory(
                total=len(index), retained=len(self._index), ratio=self._ratio
            )
        }

    def fetch_all(self) -> Iterator[RawDocument]:
        """Les clés dans l'ordre, pour un run reproductible. Chacune quitte l'index une
        fois émise."""
        index = self._discovered_index()
        for key in sorted(index):
            facets = self._read_facets(key, sorted(index.pop(key)))
            if facets:
                yield self._raw_document(key, facets)
        self._index = None

    def read_counted(self, path: str) -> ET.Element | None:
        """``None`` pour un fichier illisible, compté et détaillé."""
        try:
            return read_root(Path(path))
        except ET.ParseError as exc:
            unreadable = UnreadableFile(
                source=self._source, key=Path(path).stem, path=path, error=str(exc)
            )
            self._discard(unreadable, REASON_UNREADABLE)
            return None

    def reject_id_mismatch(self, path: str, found: str | None, key: str) -> None:
        logger.warning(
            "Fichier %s écarté : son <ID> (%s) n'est pas son nom (%s)", path, found, key
        )
        mismatch = MismatchedFile(
            source=self._source, key=key, path=path, found_id=found
        )
        self._discard(mismatch, REASON_ID_MISMATCH)

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    def _discard(self, problem: FileProblem, reason: str) -> None:
        """Compté sous ``reason``, détaillé dans ``problems``."""
        self.problems.append(problem)
        self.skip(reason)

    def _sample(self, index: dict[str, list[str]]) -> dict[str, list[str]]:
        """Sans copie à 1 : l'index tient tout le stock."""
        if self._ratio >= FULL_RATIO:
            return index
        return {key: index[key] for key in select_keys(index.keys(), self._ratio)}

    def _discovered_index(self) -> dict[str, list[str]]:
        if self._index is None:
            msg = f"{self._source.value} : `discover()` doit précéder `fetch_all()`."
            raise RuntimeError(msg)
        return self._index

    def _read_facets(self, key: str, paths: list[str]) -> tuple[Facet, ...]:
        """Une facette écartée n'emporte pas les autres."""
        facets: list[Facet] = []
        for path in paths:
            root = self.read_counted(path)
            if root is None:
                continue
            found = locate_id(root)
            if found != key:
                self.reject_id_mismatch(path, found, key)
                continue
            facets.append(Facet(path, to_tree(root), Path(path).stat().st_mtime_ns))
        arbitration = arbitrate(self._source, key, facets)
        self.collisions.extend(arbitration.collisions)
        for copy in arbitration.superseded:
            self._discard(copy, REASON_SUPERSEDED)
        return arbitration.kept

    def _raw_document(self, key: str, facets: tuple[Facet, ...]) -> RawDocument:
        return RawDocument(
            source=self._source,
            source_document_id=key,
            payload={
                # Une liste, même d'une facette : fusion et cas simple, même chemin
                "content": [facet.tree for facet in facets],
                "files": [facet.path for facet in facets],
            },
            fetched_at=datetime.now(UTC),
        )
