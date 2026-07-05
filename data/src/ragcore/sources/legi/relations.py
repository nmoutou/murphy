from collections import defaultdict

import networkx as nx

from ragcore.core.models import (
    OwnerId,
    ParsedDocument,
    Relation,
    RelationType,
    SourceName,
)
from ragcore.core.models.identifiers import ELI


def _source_identifier_from(s: str) -> ELI:
    """Crée un ELI depuis une string — pour les relations LEGI."""
    return ELI(raw=s)


class LegiRelationExtractor:
    source_name = SourceName.LEGI

    def __init__(
        self,
        allowed_types: list[str] | None = None,
        relation_renames: dict[str, str] | None = None,
    ) -> None:
        self._allowed_types = allowed_types or [t.value for t in RelationType]
        self._relation_renames = relation_renames or {}

    def extract(self, document: ParsedDocument) -> list[Relation]:
        raw_relations = self._extract_raw(document)
        normalized = self._normalize(raw_relations)
        filtered = self._filter(normalized)
        inverted = self._invert(filtered)
        renamed = self._rename(inverted)
        reduced = self._reduce(renamed)
        return reduced

    def _extract_raw(self, document: ParsedDocument) -> list[dict]:
        """Extrait les références depuis document.structure."""
        refs = document.structure.get("references", [])
        return refs if isinstance(refs, list) else []

    def _normalize(self, raw: list[dict]) -> list[Relation]:
        relations = []
        for ref in raw:
            try:
                rel = Relation(
                    source_identifier=_source_identifier_from(ref.get("source", "")),
                    target_identifier=_source_identifier_from(ref.get("target", "")),
                    relation_type=RelationType(ref.get("type", "cites")),
                    owner_id=ref.get("owner_id", ""),
                    source=SourceName.LEGI,
                    metadata=ref.get("metadata", {}),
                )
                relations.append(rel)
            except (ValueError, KeyError):
                continue
        return relations

    def _filter(self, relations: list[Relation]) -> list[Relation]:
        return [r for r in relations if r.relation_type.value in self._allowed_types]

    def _invert(self, relations: list[Relation]) -> list[Relation]:
        """Crée des relations inversées — NOUVEAUX objets, jamais de mutation in-place."""
        result = list(relations)
        for rel in relations:
            inverted = Relation(
                source_identifier=rel.target_identifier,
                target_identifier=rel.source_identifier,
                relation_type=rel.relation_type,
                owner_id=rel.owner_id,
                source=rel.source,
                metadata=rel.metadata,
            )
            result.append(inverted)
        return result

    def _reduce(self, relations: list[Relation]) -> list[Relation]:
        """Réduction transitive par type de relation.

        Pour chaque ``relation_type``, construit un DAG des relations et applique
        ``nx.transitive_reduction`` pour éliminer les arêtes redondantes
        (A→B, B→C, A→C devient A→B, B→C). Les cycles sont préservés tels quels
        car la réduction transitive n'est définie que sur les DAGs.
        """
        if not relations:
            return relations

        by_type: dict[tuple[RelationType, OwnerId], list[Relation]] = defaultdict(list)
        for rel in relations:
            by_type[(rel.relation_type, rel.owner_id)].append(rel)

        result: list[Relation] = []
        for (rel_type, owner_id), group in by_type.items():
            graph: nx.DiGraph = nx.DiGraph()
            edge_metadata: dict[tuple[str, str], dict] = {}
            for rel in group:
                edge = (str(rel.source_identifier.raw), str(rel.target_identifier.raw))
                graph.add_edge(*edge)
                edge_metadata.setdefault(edge, rel.metadata)

            if nx.is_directed_acyclic_graph(graph):
                reduced_graph = nx.transitive_reduction(graph)
                kept_edges = set(reduced_graph.edges())
            else:
                kept_edges = set(graph.edges())

            for src, tgt in kept_edges:
                result.append(
                    Relation(
                        source_identifier=ELI(raw=src),
                        target_identifier=ELI(raw=tgt),
                        relation_type=rel_type,
                        owner_id=owner_id,
                        source=group[0].source,
                        metadata=edge_metadata.get((src, tgt), {}),
                    )
                )
        return result

    def _rename(self, relations: list[Relation]) -> list[Relation]:
        if not self._relation_renames:
            return relations
        result = []
        for rel in relations:
            new_type_val = self._relation_renames.get(
                rel.relation_type.value, rel.relation_type.value
            )
            try:
                new_type = RelationType(new_type_val)
            except ValueError:
                new_type = rel.relation_type
            result.append(
                Relation(
                    source_identifier=rel.source_identifier,
                    target_identifier=rel.target_identifier,
                    relation_type=new_type,
                    owner_id=rel.owner_id,
                    source=rel.source,
                    metadata=rel.metadata,
                )
            )
        return result
