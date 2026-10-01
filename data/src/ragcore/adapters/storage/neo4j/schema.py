"""Le schéma du graphe : la contrainte d'unicité des nœuds documents.

Un index Neo4j se rattache toujours à un label. Sans elle, toute recherche par
``identifier`` parcourrait tous les nœuds, et rien n'empêcherait deux nœuds de partager
un identifiant. ``drop_all`` (``MATCH (n) DETACH DELETE n``) la laisse en place.
"""

import neo4j

from .node_properties import DOCUMENT_LABEL

__all__ = ["DOCUMENT_IDENTIFIER_CONSTRAINT", "ensure_graph_constraints"]

DOCUMENT_IDENTIFIER_CONSTRAINT = "document_identifier"

_CREATE_CONSTRAINT = (
    f"CREATE CONSTRAINT {DOCUMENT_IDENTIFIER_CONSTRAINT} IF NOT EXISTS"
    f" FOR (d:{DOCUMENT_LABEL}) REQUIRE d.identifier IS UNIQUE"
)


async def ensure_graph_constraints(driver: neo4j.AsyncDriver) -> None:
    """Pose la contrainte d'unicité de ``(:Document).identifier``. Idempotent."""
    async with driver.session() as session:
        await session.run(_CREATE_CONSTRAINT)
