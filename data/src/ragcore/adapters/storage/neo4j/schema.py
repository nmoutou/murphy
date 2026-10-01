"""La contrainte d'unicité des nœuds documents, qui sert aussi d'index. ``drop_all`` la
laisse en place.
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
    """Idempotent."""
    async with driver.session() as session:
        await session.run(_CREATE_CONSTRAINT)
