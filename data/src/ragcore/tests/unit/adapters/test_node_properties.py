"""Les labels d'un nœud document : ``Document``, plus celui de son type."""

import re

from ragcore.adapters.storage.neo4j.node_properties import DOCUMENT_LABEL, TYPE_LABELS
from ragcore.core.models.enums import DocumentType

_CYPHER_LABEL = re.compile(r"[A-Z][A-Za-z0-9]*")


def test_chaque_type_de_document_a_son_label() -> None:
    """Un type sans label ferait échouer l'écriture de chacun de ses nœuds."""
    assert set(TYPE_LABELS) == set(DocumentType)


def test_les_labels_sont_distincts_et_bien_formes() -> None:
    labels = [DOCUMENT_LABEL, *TYPE_LABELS.values()]

    assert len(set(labels)) == len(labels)
    assert all(_CYPHER_LABEL.fullmatch(label) for label in labels)
