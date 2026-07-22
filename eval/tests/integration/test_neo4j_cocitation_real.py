"""Test d'intégration : le vrai chemin de lecture Neo4j du miner de co-citation.

On peuple un Neo4j éphémère (testcontainers) au **format d'ingestion** — nœuds
identifiés par ``{identifier, owner_id}`` avec label métier, arêtes typées par le
verbe — puis on vérifie que ``Neo4jCocitationMiner`` :

- rend les paires ``(source, verbe, target)`` triées ;
- **exclut** les arêtes touchant un ``:Pending`` ;
- **exclut** les nœuds hors du contrat documentaire (garde-fou de dérive de
  ``_DOCUMENT_LABELS``) ;
- **exclut** les auto-paires (``a = a``) ;
- **exclut** l'autre tenant (filtre ``owner_id``) ;
- **échoue franchement** sur un nœud sans ``identifier``.

C'est la preuve que le Cypher — le lieu réel de ces filtres — tient contre un vrai
serveur ; une doublure en mémoire ne l'exécute jamais.

Deux scénarios, **un seul conteneur** : les cas nominal et dégradé sont isolés par
``owner_id`` (le filtre tenant est déjà dans la requête), ce qui évite de payer un
second démarrage de Neo4j. Il le faut car le cas « nœud sans ``identifier`` » lève
``ValueError`` : mêlé au seed nominal, il ferait échouer l'assertion de liste.

Hors CI par défaut (marker ``integration``, nécessite Docker).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

neo4j_container = pytest.importorskip("testcontainers.neo4j")

from testcontainers.neo4j import Neo4jContainer  # noqa: E402

from murphy_eval.adapters.graph.neo4j_cocitation import (  # noqa: E402
    Neo4jCocitationMiner,
)
from murphy_eval.core.models.cocitation import CocitationPair  # noqa: E402

_OWNER = "system"
_OTHER_OWNER = "tenant-x"
_BROKEN_OWNER = "tenant-broken"

# Graphe de départ. Format d'ingestion : chaque nœud porte identifier + owner_id,
# les arêtes portent le verbe comme TYPE (pas comme propriété).
#
# Chaque cas dégradé est RELIÉ à un vrai document : sans arête, il ne serait pas
# candidat au MATCH et le test ne prouverait rien.
_SEED = """
CREATE (a:Article {identifier: 'eli:A', owner_id: $owner})
CREATE (b:Article {identifier: 'eli:B', owner_id: $owner})
CREATE (c:Article {identifier: 'eli:C', owner_id: $owner})
CREATE (p:Pending {identifier: 'eli:P', owner_id: $owner})
CREATE (k:Chunk   {identifier: 'chunk:1', owner_id: $owner})
CREATE (x:Article {identifier: 'eli:X', owner_id: $other})
CREATE (y:Article {identifier: 'eli:Y', owner_id: $other})
CREATE (a)-[:cites]->(b)
CREATE (a)-[:succeeded_by]->(c)
CREATE (b)-[:cites]->(p)
CREATE (a)-[:cites]->(k)
CREATE (a)-[:cites]->(a)
CREATE (x)-[:cites]->(y)
"""

# Tenant à part : un nœud portant un label DOCUMENTAIRE mais sans `identifier`. Le
# filtre de labels le laisse passer (il est :Article) — c'est donc le mapping qui doit
# l'intercepter, et c'est exactement ce que le second test vérifie.
#
# Ce cas est la raison pour laquelle l'auto-arête s'exclut par `NOT (a = b)` et non par
# `a.identifier <> b.identifier` : ce dernier vaut NULL ici (jamais TRUE) et ferait
# disparaître la ligne en silence, sans jamais atteindre le fail-fast.
_BROKEN_SEED = """
CREATE (a:Article {identifier: 'eli:BA', owner_id: $owner})
CREATE (n:Article {owner_id: $owner})
CREATE (a)-[:cites]->(n)
"""


@pytest.fixture(scope="module")
def miner() -> Iterator[Neo4jCocitationMiner]:
    """Un Neo4j peuplé une fois pour les deux scénarios (le démarrage coûte des s)."""
    with Neo4jContainer("neo4j:5.26") as container:
        driver = container.get_driver()
        with driver.session() as session:
            session.run(_SEED, owner=_OWNER, other=_OTHER_OWNER)
            session.run(_BROKEN_SEED, owner=_BROKEN_OWNER)
        driver.close()

        auth = ("neo4j", container.password)  # défaut testcontainers
        # Gestionnaire de contexte : la connexion se ferme même si un test lève.
        with Neo4jCocitationMiner(
            container.get_connection_url(), auth=auth
        ) as instance:
            yield instance


@pytest.mark.integration
def test_mine_pairs_filtre_pending_auto_autre_tenant_et_non_documents(
    miner: Neo4jCocitationMiner,
) -> None:
    """Seules les arêtes document→document du tenant remontent, triées.

    Écartés : le ``:Pending`` (cible jamais arrivée), le ``:Chunk`` (hors contrat
    documentaire), l'auto-arête (trivialement vraie), l'autre tenant.
    """
    pairs = miner.mine_pairs(owner_id=_OWNER)

    assert pairs == [
        CocitationPair(source="eli:A", verb="cites", target="eli:B"),
        CocitationPair(source="eli:A", verb="succeeded_by", target="eli:C"),
    ]


@pytest.mark.integration
def test_mine_pairs_fail_fast_sur_noeud_sans_identifier(
    miner: Neo4jCocitationMiner,
) -> None:
    """Un nœud hors contrat fait échouer le minage, au lieu de produire ``"None"``."""
    with pytest.raises(ValueError, match="incohérent"):
        miner.mine_pairs(owner_id=_BROKEN_OWNER)
