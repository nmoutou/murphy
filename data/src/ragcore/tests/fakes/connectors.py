from ragcore.core.models.document import RawDocument
from ragcore.core.ports.connector import BaseConnector


def read_source(connector: BaseConnector) -> list[RawDocument]:
    """Les deux passes, comme le nœud `connect`."""
    connector.discover()
    return list(connector.fetch_all())
