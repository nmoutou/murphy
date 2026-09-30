"""Le connecteur de jurisprudence — **un fichier, un document**. Et c'est tout.

**Il est plus simple que celui de LEGI, et il faut dire pourquoi.** LEGI impose deux
complications que la juri n'a pas :

- **la fusion de facettes** — ``TEXTE_VERSION`` et ``TEXTELR`` sont le *même* document
  dans deux fichiers (98 IDs, intersection 98/98), et les émettre séparément produirait
  98 collisions d'identifiant. La juri ne fait pas ça : mesuré, chaque ``<ID>`` du corpus
  apparaît dans exactement un fichier.
- **les artefacts d'export** — 1637 des 2564 fichiers LEGI sont des ``versions.xml`` sans
  contenu. La juri n'en a aucun.

Le connecteur juri n'a donc rien à décider. Il localise, il lit, il emballe.

**Une seule classe pour cinq sources.** CAPP, CASS, INCA, JADE et CONSTIT ne diffèrent que
par leur racine — et la racine ne l'intéresse pas : c'est le parser qui l'interprète, via
la table de rôles. Le connecteur prend un chemin et un ``SourceName``, et rend des
``RawDocument``. Écrire cinq connecteurs identiques à un nom près aurait été le contraire
exact de ce que §3 demande.

**« Idiot » veut dire quelque chose de précis.** Il ne sait pas ce qu'est un ``<LIEN>``,
ni une juridiction, ni une formation de jugement. Il sait qu'un XML est un arbre, qu'un
dict est un arbre, et il transcrit. Si DILA ajoute une balise demain, il la transporte
sans broncher — et c'est le parser qui la déclarera inconnue.
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
    """``BaseConnector`` sur une arborescence XML de jurisprudence.

    Instancié **une fois par base** — cinq instances, une classe. La base est un
    paramètre (``source``), pas un type : c'est très exactement ce que le principe
    directeur exige (« pas de typage métier — le type de fichier métier est un simple
    champ »).
    """

    def __init__(self, root: Path | str, source: SourceName) -> None:
        self._root = Path(root)
        self._source = source
        self.skipped: dict[str, int] = {}
        """Ce que le connecteur a écarté, et pourquoi.

        Vide en pratique : la juri n'a pas d'artefact d'export. Le champ existe quand même
        parce que le port l'expose, et parce qu'un fichier illisible doit pouvoir être
        compté plutôt que disparaître.
        """

    @property
    def source_name(self) -> SourceName:
        return self._source

    async def fetch_all(self) -> AsyncIterator[RawDocument]:
        """Itère les documents : un fichier XML, un ``RawDocument``.

        **Aucun regroupement.** Là où LEGI doit lire tous les fichiers avant d'émettre
        quoi que ce soit (pour fusionner les facettes d'un même texte), la juri émet au
        fil de l'eau : le corpus n'est jamais chargé en mémoire, même partiellement.
        """
        self.skipped = {}

        for path in sorted(self._root.rglob("*.xml")):
            root = read_root(path)
            if root is None:
                # Illisible : il n'y a rien à parser, et le parser n'en saurait rien. On
                # le COMPTE — écarter sans compter serait un skip silencieux.
                self._skip(REASON_UNREADABLE)
                continue

            yield RawDocument(
                source=self._source,
                source_document_id=locate_id(root) or str(path),
                payload={
                    # Une LISTE d'une seule facette. Le parser générique attend une liste
                    # (LEGI en fusionne parfois deux) : rendre un dict ici forcerait le
                    # parser à connaître la différence entre ses sources — exactement ce
                    # qu'on lui épargne.
                    "content": [to_tree(root)],
                    "files": [str(path)],
                },
                fetched_at=datetime.now(UTC),
            )

    def _skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1
