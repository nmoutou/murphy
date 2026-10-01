"""CLIQUET — les renommages de métadonnées (ADR-049).

Une collision de valeurs se voit au run : la collection ``MURPHY_META.collisions`` la
montre. Une collision de NOMS, elle, est une décision de la table, et rien ne la verrait
au run : deux balises renommées pareil, un renommage commun redéfini en silence, une
cible qui écrase un champ du contrat. Ce cliquet les interdit.
"""

from __future__ import annotations

import pytest

from ragcore.sources.generic import RoleTable
from ragcore.sources.jurisprudence.table import _COMMON_RENAMES, ROLE_TABLE_BY_ROOT
from ragcore.sources.legislatif.table import LEGI_ROLE_TABLE

TABLES: dict[str, RoleTable] = {"LEGI": LEGI_ROLE_TABLE, **ROLE_TABLE_BY_ROOT}

RESERVED_FIELDS = frozenset(
    {
        # Le contrat de serving, posé dans le payload Qdrant (`QdrantVectorRepository`).
        "chunk_id",
        "identifier",
        "char_start",
        "char_end",
        "document_type",
        "nature",
        # Les propriétés d'un nœud Neo4j, que `node_props` complète des métadonnées.
        "title",
        "source",
    }
)
"""Les champs qu'une métadonnée homonyme écraserait, ou masquerait."""


@pytest.mark.parametrize("name", TABLES)
def test_une_cible_n_apparait_qu_une_fois(name: str) -> None:
    targets = list(TABLES[name].meta_renames.values())
    duplicates = {target for target in targets if targets.count(target) > 1}
    assert not duplicates, f"{name} : plusieurs balises renommées en {duplicates}"


@pytest.mark.parametrize("name", TABLES)
def test_aucune_cible_n_est_un_champ_reserve(name: str) -> None:
    reserved = RESERVED_FIELDS & set(TABLES[name].meta_renames.values())
    assert not reserved, f"{name} : cible réservée {reserved}"


@pytest.mark.parametrize("name", TABLES)
def test_une_cle_list_est_une_cible_de_renommage(name: str) -> None:
    """Une clé non renommée devient une liste sans déclaration : la déclarer ne sert à
    rien, et trahit une faute de frappe."""
    table = TABLES[name]
    orphans = table.list_keys - set(table.meta_renames.values())
    assert not orphans, f"{name} : clés list sans renommage {orphans}"


@pytest.mark.parametrize("root", ROLE_TABLE_BY_ROOT)
def test_aucune_table_juri_ne_redefinit_un_renommage_commun(root: str) -> None:
    """``{**_COMMON_RENAMES, **renames}`` laisserait une table écraser un renommage
    commun sans un mot. S'il doit différer, il sort de la liste commune."""
    renames = ROLE_TABLE_BY_ROOT[root].meta_renames
    redefined = {
        tag for tag, target in _COMMON_RENAMES.items() if renames[tag] != target
    }
    assert not redefined, f"{root} : renommages communs redéfinis {redefined}"
