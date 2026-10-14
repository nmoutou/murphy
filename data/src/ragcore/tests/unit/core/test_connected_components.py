"""L'union-find de la phase 2 : une entrée par nœud, la taille de chaque composante."""

from ragcore.core.services.connected_components import Component, ConnectedComponents


def _components(*edges: tuple[str, str]) -> list[Component]:
    found = ConnectedComponents()
    for source, target in edges:
        found.add_edge(source, target)
    return found.components()


def test_two_disjoint_edges_are_two_components() -> None:
    assert _components(("a", "b"), ("c", "d")) == [
        Component("a", ("a", "b"), 1),
        Component("c", ("c", "d"), 1),
    ]


def test_a_shared_node_joins_two_trees() -> None:
    """``t → s``, ``s → a``, et ``u → a`` : un seul arbre, quel que soit l'ordre."""
    assert _components(("t", "s"), ("u", "a"), ("s", "a")) == [
        Component("a", ("a", "s", "t", "u"), 3)
    ]


def test_duplicates_and_cycles_count_every_relation() -> None:
    """Une arête déclarée par deux documents est deux lignes à supprimer."""
    assert _components(("a", "b"), ("a", "b"), ("b", "a"), ("c", "c")) == [
        Component("a", ("a", "b"), 3),
        Component("c", ("c",), 1),
    ]


def test_the_components_do_not_depend_on_the_reading_order() -> None:
    edges = [("e", "f"), ("b", "c"), ("a", "b"), ("f", "g"), ("d", "e")]

    assert _components(*edges) == _components(*reversed(edges))


def test_a_long_chain_is_one_component() -> None:
    edges = [(f"n{i:05d}", f"n{i + 1:05d}") for i in range(5000)]

    (component,) = _components(*reversed(edges))

    assert (len(component.nodes), component.relations) == (5001, 5000)


def test_listing_the_components_empties_the_union_find() -> None:
    found = ConnectedComponents()
    found.add_edge("a", "b")

    found.components()

    assert found.components() == []
