"""La réduction transitive, une règle du domaine.

Seule la contenance est transitive : un article dans un chapitre dans un livre est
dans le livre. Réduire des citations détruirait des faits (« A cite B, B cite C, A cite
C » sont trois citations réelles).

LEGI déclare la hiérarchie de deux côtés : ``<CONTEXTE>`` donne la fermeture
transitive, ``<STRUCTURE_TA>`` l'arbre, dans les fichiers des sections (seul, il ne
couvre que 370 articles sur 384). Leur union est la fermeture ; la réduire redonne
l'arbre. Elle ne se voit qu'en tête de la phase 2, jamais document par document.
"""

from collections import defaultdict

import networkx as nx

from ..links.vocabulary import CONTIENT, RelationVerb
from ..models.relation import Relation

__all__ = ["REDUCIBLE_TYPES", "reduce_transitively"]

REDUCIBLE_TYPES: frozenset[RelationVerb] = frozenset({CONTIENT})
"""Liste blanche : un verbe brut non traduit n'est jamais réduit, faute de connaître son
algèbre."""


def reduce_transitively(
    relations: list[Relation],
    reducible: frozenset[RelationVerb] = REDUCIBLE_TYPES,
) -> list[Relation]:
    """Réduit la fermeture transitive en arbre, verbe par verbe ; les autres verbes
    traversent intacts.

    Un cycle rend la réduction indéfinie : le sous-graphe est alors conservé tel quel.
    """
    if not relations:
        return relations

    kept: list[Relation] = []
    to_reduce: dict[str, list[Relation]] = defaultdict(list)

    for relation in relations:
        if relation.relation_type in reducible:
            to_reduce[relation.relation_type].append(relation)
        else:
            kept.append(relation)

    for group in to_reduce.values():
        kept.extend(_reduce_group(group))

    return kept


def _reduce_group(group: list[Relation]) -> list[Relation]:
    """Rend les arêtes conservées d'un groupe de même verbe."""
    graph: nx.DiGraph = nx.DiGraph()
    # networkx ne rend que des couples de chaînes : ce registre retrouve les relations,
    # avec leurs métadonnées
    by_edge: dict[tuple[str, str], Relation] = {}

    for relation in group:
        edge = (
            relation.source_identifier.serialize(),
            relation.target_identifier.serialize(),
        )
        graph.add_edge(*edge)
        by_edge.setdefault(edge, relation)

    if graph.number_of_edges() == 0:
        return []

    if not nx.is_directed_acyclic_graph(graph):
        # Un cycle de contenance est une anomalie du corpus : laissée visible
        return list(by_edge.values())

    surviving = set(nx.transitive_reduction(graph).edges())
    return [relation for edge, relation in by_edge.items() if edge in surviving]
