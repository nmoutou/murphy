"""Le connecteur de fichiers LEGI — il localise, il lit, il emballe. Il n'interprète pas.

**Ce que « idiot » veut dire ici.** Le connecteur ne sait pas ce qu'est un ``<LIEN>``,
ni un identifiant, ni une section. Il sait une seule chose : *un XML est un arbre, un dict est
un arbre, je transcris*. Aucune sémantique LEGI ne vit dans ce module. Si demain LEGI
ajoute une balise, il la transporte sans broncher — et c'est le parser qui la déclarera
inconnue.

**Pourquoi un arbre et pas un dict à plat.** Aplatir, c'est déjà interpréter : il faut
choisir quoi joindre, quoi écraser. Et surtout : ``<LIENS>`` contient N ``<LIEN>``
frères, qu'un dict plat écraserait mutuellement — 23 liens deviendraient 1. La
transcription en arbre est la seule qui soit SANS PERTE, et « sans perte » est
exactement le critère de l'idiotie du connecteur.

Il prend malgré tout deux décisions. Aucune ne regarde le contenu :

**1. Il écarte les artefacts d'export.** 1637 des 2564 fichiers du corpus sont des
``versions.xml`` : une ligne, un ID nu, ni contenu ni relation. Ce ne sont pas des
documents — ce sont des résidus de l'export. Les passer au parser produirait 1637
rejets qui noieraient les vrais sous 64 % de bruit connu. Le manifest est un registre
de *tentatives de traitement d'un document* : y inscrire un ``versions.xml`` en
EXCLUDED, ce serait mentir sur ce qu'il est.

Ce n'est pas un skip silencieux : le connecteur COMPTE ce qu'il écarte
(``self.skipped``). Et il n'écarte jamais sur le seul nom de fichier — il vérifie que
la racine est bien ``<VERSIONS>``. Décider qu'un chemin n'est pas un document est un
acte de *localisation*, pas d'interprétation : c'est la même compétence que « lister
les ``*.xml`` ».

**2. Il fusionne les deux facettes d'un même texte.** ``TEXTE_VERSION`` et ``TEXTELR``
sont le MÊME document — mesuré : 98 IDs chacun, intersection 98/98. Le premier porte le
titre et les métadonnées, le second la structure et AUCUN titre. Émettre un
``RawDocument`` par fichier donnerait 98 collisions d'identifiant : le dispatch par clé les
enverrait au même worker, la saga écrirait l'un puis l'autre l'écraserait — et **les 98
textes du corpus finiraient sans titre**. Grouper par identifiant n'est pas une
optimisation, c'est ce qui empêche une perte de données silencieuse.
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
"""Les deux formes que prend l'artefact d'export (mesuré : 1637 ``<VERSIONS>``, 60
``<ID>`` — ces derniers sont des fichiers d'UNE LIGNE, réduits à un identifiant nu).

Aucune des deux ne porte de contenu, de titre ou de relation. Ce ne sont pas des
documents pauvres : ce ne sont pas des documents."""


class LegiFileConnector:
    """Implémentation de ``BaseConnector`` sur une arborescence XML locale."""

    source_name = SourceName.LEGI

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)
        self.skipped: dict[str, int] = {}
        """Ce que le connecteur a écarté, et pourquoi. Lu par le node qui ouvre le run.

        Écarter sans compter serait un skip silencieux ; c'est le compte qui fait la
        différence entre « ignoré » et « caché »."""

    async def fetch_all(self) -> AsyncIterator[RawDocument]:
        """Itère les documents de la source, un par identifiant.

        Générateur : le corpus n'est jamais entièrement chargé en mémoire. Le
        regroupement par identifiant impose en revanche de connaître tous les fichiers
        d'un même document avant de l'émettre — donc de lire les arbres avant de
        rendre la main. C'est le prix de la fusion, et il se paie en mémoire des
        seuls arbres, pas des RawDocument.
        """
        self.skipped = {}
        by_identifier: dict[str, list[tuple[Path, dict[str, Any]]]] = {}

        for path in sorted(self._root.rglob("*.xml")):
            root = read_root(path)
            if root is None:
                # Illisible : pas d'arbre à transcrire. Le parser n'en saura jamais
                # rien — donc si le connecteur ne le compte pas ici, ce fichier
                # disparaît AVANT même d'entrer dans `seen` : une perte invisible à
                # l'équation de complétude. On l'écarte en le COMPTANT.
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
                    # Une LISTE de facettes, même quand il n'y en a qu'une. Un dict à
                    # clé unique aurait fait du cas normal la règle et de la fusion une
                    # exception à tester ; ici les deux empruntent le même chemin.
                    "content": [tree for _, tree in facets],
                    "files": [str(path) for path, _ in facets],
                },
                fetched_at=datetime.now(UTC),
            )

    def _is_export_artifact(self, path: Path, root: ET.Element) -> bool:
        """Le nom ET la racine. Jamais le nom seul.

        Un fichier nommé ``versions.xml`` dont la racine serait ``<ARTICLE>`` est un
        document, et il doit être émis. Écarter sur le nom seul, c'est faire d'une
        convention de nommage une règle métier — et perdre le jour où elle change.
        """
        return path.name == _EXPORT_ARTIFACT_NAME and root.tag in _EXPORT_ARTIFACT_ROOTS

    def _skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1
