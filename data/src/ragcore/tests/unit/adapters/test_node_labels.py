"""La table des labels Neo4j : ce qui finit dans le texte d'une requête Cypher."""

import pytest

from ragcore.adapters.storage.neo4j.node_properties import DEFAULT_LABEL, NodeLabels
from ragcore.core.models.identifiers import Identifier


def test_un_prefixe_hors_table_recoit_le_repli() -> None:
    labels = NodeLabels(by_prefix={"LEGIARTI": "Article"})

    assert labels.label_for(Identifier(raw="JURITEXT000019333891")) == DEFAULT_LABEL
    assert labels.known == (DEFAULT_LABEL, "Article")


@pytest.mark.parametrize(
    ("by_prefix", "message"),
    [
        ({"ARTI": "Article"}, "Préfixe"),
        ({"LEGIARTI": "Mon Label"}, "Label"),
        ({"LEGIARTI": "Pending"}, "réservé"),
    ],
)
def test_un_label_ou_un_prefixe_mal_forme_leve(
    by_prefix: dict[str, str], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        NodeLabels(by_prefix=by_prefix)
