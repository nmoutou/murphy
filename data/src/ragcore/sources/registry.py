"""Le registre des sources — **une source, quatre données**. Rien de plus.

**Ce que ce module empêche.** Sans lui, le hook ferait :

    if source == "legi":     connector, table = LegiFileConnector(…), LEGI_ROLE_TABLE
    elif source == "cass":   connector, table = JuriFileConnector(…), JURI_JUDI_ROLE_TABLE
    elif source == "jade":   …

Six branches aujourd'hui, et une de plus à chaque source. C'est le « branchement
conditionnel » que la doctrine remplace partout par de la **donnée déclarative** — la
table de rôles pour les balises, le catalogue pour les events, la table de traduction pour
les verbes. Ici c'est le même motif, appliqué au dernier endroit qui y échappait.

**Ce que la doctrine dit, et qui est plus fort que « c'est plus joli ».** *« Pas de typage
métier — le type de fichier métier est un simple champ. La différenciation se joue entre
les bases, pas dans une hiérarchie de types Python. »* Une source n'est pas une classe :
c'est une ligne dans un dictionnaire.

**La nuance qui compte : le connecteur est une FABRIQUE, pas une instance.** Il tient un
chemin, et le chemin dépend de la configuration d'infrastructure — qui n'est connue qu'à
l'exécution. La table de rôles, elle, est une constante : elle ne dépend de rien.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ragcore.core.models.enums import SourceName
from ragcore.sources.generic import RoleTable
from ragcore.sources.jurisprudence import (
    JURI_ADMIN_ROLE_TABLE,
    JURI_CONSTIT_ROLE_TABLE,
    JURI_JUDI_ROLE_TABLE,
    JuriFileConnector,
)
from ragcore.sources.legislatif.file_connector import LegiFileConnector
from ragcore.sources.legislatif.table import LEGI_NODE_LABELS, LEGI_ROLE_TABLE

__all__ = ["SOURCES", "SourceDefinition", "definition_for", "node_labels_by_prefix"]


@dataclass(frozen=True)
class SourceDefinition:
    """Tout ce que ragcore doit savoir d'une source. **Quatre choses.**"""

    connector: Callable[[Path], Any]
    """Comment localiser et transcrire ses fichiers. Une fabrique : le chemin vient de
    l'infrastructure, donc de l'exécution."""

    table: RoleTable
    """Comment interpréter ce qu'on a transcrit. Une constante : elle ne dépend de rien."""

    subdirectory: str
    """Le sous-répertoire du corpus (``LEGI``, ``CASS``…).

    Le chemin racine est de l'infrastructure (``xml_source_path``, dans ``.env``) ; le
    sous-répertoire est un fait sur la source. Les mélanger obligerait à changer la config
    pour ingérer une autre base.
    """

    node_labels: Mapping[str, str] = field(default_factory=dict)
    """Le label Neo4j de ses documents, d'après le préfixe de l'identifiant. Un préfixe
    absent reçoit le repli ``Document`` (``node_properties.DEFAULT_LABEL``)."""


SOURCES: Mapping[SourceName, SourceDefinition] = {
    SourceName.LEGI: SourceDefinition(
        connector=lambda root: LegiFileConnector(root),
        table=LEGI_ROLE_TABLE,
        subdirectory="LEGI",
        node_labels=LEGI_NODE_LABELS,
    ),
    # ── Les cinq sources de jurisprudence ──────────────────────────────────────
    #
    # **Cinq lignes. Aucun parser, aucun connecteur nouveau.** CAPP, CASS et INCA
    # partagent la MÊME table : elles publient la même racine (`TEXTE_JURI_JUDI`), et la
    # base n'est qu'un champ. C'est la vérification de §3, et elle se lit ici :
    # ajouter une source, c'est ajouter une ligne.
    SourceName.CAPP: SourceDefinition(
        connector=lambda root: JuriFileConnector(root, SourceName.CAPP),
        table=JURI_JUDI_ROLE_TABLE,
        subdirectory="CAPP",
    ),
    SourceName.CASS: SourceDefinition(
        connector=lambda root: JuriFileConnector(root, SourceName.CASS),
        table=JURI_JUDI_ROLE_TABLE,
        subdirectory="CASS",
    ),
    SourceName.INCA: SourceDefinition(
        connector=lambda root: JuriFileConnector(root, SourceName.INCA),
        table=JURI_JUDI_ROLE_TABLE,
        subdirectory="INCA",
    ),
    SourceName.JADE: SourceDefinition(
        connector=lambda root: JuriFileConnector(root, SourceName.JADE),
        table=JURI_ADMIN_ROLE_TABLE,
        subdirectory="JADE",
    ),
    SourceName.CONSTIT: SourceDefinition(
        connector=lambda root: JuriFileConnector(root, SourceName.CONSTIT),
        table=JURI_CONSTIT_ROLE_TABLE,
        subdirectory="CONSTIT",
    ),
}
"""Les sources que ragcore sait ingérer. **Une donnée, pas un branchement.**

``JORF`` et ``UPLOAD`` existent dans ``SourceName`` mais pas ici : leur connecteur n'est
pas écrit. C'est honnête — une source absente de ce registre lève une erreur nette au
démarrage, plutôt que de partir sur un `else` qui ingérerait n'importe quoi.
"""


def definition_for(source: SourceName) -> SourceDefinition:
    """La définition d'une source. Lève si elle n'est pas connue.

    **Un ``KeyError`` nu ne dirait rien d'utile.** Celui-ci nomme les sources disponibles :
    l'erreur qu'on lit à 3 h du matin doit contenir sa propre réponse.
    """
    definition = SOURCES.get(source)
    if definition is None:
        connues = ", ".join(sorted(s.value for s in SOURCES))
        msg = (
            f"Source non ingérable : {source.value!r}. "
            f"Aucun connecteur ni table ne lui est associé. Sources connues : {connues}."
        )
        raise ValueError(msg)
    return definition


def all_sources() -> tuple[SourceName, ...]:
    """Toutes les sources ingérables — ce qu'un ``kedro run`` nu doit traiter.

    **C'est ``SOURCES`` qui fait foi, pas ``SourceName``.** L'enum déclare le vocabulaire
    (``JORF``, ``UPLOAD``…) ; ce registre déclare ce qui est réellement *ingérable*.
    Dériver le défaut de l'enum ferait planter le run nu sur ``JORF``, dont le connecteur
    n'est pas écrit — et le ferait planter à chaque *ajout* de vocabulaire, ce qui
    punirait précisément le geste qu'on veut rendre anodin.

    Ordre stable (celui de ``SOURCES``) : LEGI d'abord, puis les cinq juri. Un run doit
    être reproductible jusque dans l'ordre où il lit.
    """
    return tuple(SOURCES)


def node_labels_by_prefix(
    sources: Mapping[SourceName, SourceDefinition] = SOURCES,
) -> dict[str, str]:
    """Les labels Neo4j de TOUTES les sources, pas seulement celles du run.

    La dé-hydratation d'un nœud retire tous les labels connus : un run restreint à
    ``cass`` doit pouvoir retirer ``Article`` d'un nœud LEGI. Deux sources qui donnent
    deux labels au même préfixe sont une erreur de déclaration : elle lève.
    """
    merged: dict[str, str] = {}
    for source, definition in sources.items():
        for prefix, label in definition.node_labels.items():
            if merged.get(prefix, label) != label:
                msg = (
                    f"Labels Neo4j en conflit pour le préfixe {prefix!r} : "
                    f"{merged[prefix]!r}, puis {label!r} (source {source.value!r})."
                )
                raise ValueError(msg)
            merged[prefix] = label
    return merged
