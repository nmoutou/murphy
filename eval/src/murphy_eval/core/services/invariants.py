"""Invariants structurels de strate 1 (ADR-017) — MAISON, sans annotation.

La strate 1 d'ADR-017 vérifie des propriétés *structurelles* des artefacts du
harnais, « pérennité totale, annotation aucune ». Ce module en tient la part
**pure** : des fonctions ``Run | Qrels → list[Violation]`` qui ne touchent
aucune base de données (décision de cadrage B-06) et ne présupposent que les
modèles de domaine déjà chargés.

Ce sont les garde-fous que le scorer **suppose tacitement** aujourd'hui :
``aggregate_run`` densifie les rangs et ``dedup_first`` protège les métriques à
coupe, mais rien ne vérifie qu'un run *chargé depuis un JSONL* (production
B-05, ou artefact externe) respecte l'invariant *en entrée*. Un run à rangs
troués, un doublon ``(query_id, chunk_id)`` ou un run et des qrels aux espaces
de nommage disjoints se chargeraient sinon en silence — puis le scorer rendrait
un chiffre faux (métriques à 0, ou > 1.0) sans rien signaler.

**On collecte, on ne lève pas** (par défaut) : une suite strate 1 doit dire
*tout* ce qui cloche d'un coup, pas s'arrêter à la première violation. Le
loader validant (``adapters/trec/projection.py``) est libre de transformer une
liste non vide en ``InvariantError``.

Périmètre **hors** de ce module (décisions de cadrage B-06) : complétude,
intégrité des liens Neo4j et déterminisme du *retrieval* réel — tous exigent
les bases peuplées (strate 1 *live*), et sont déjà couverts côté ``data/``. La
forme canonique stricte ``<kind>:<raw>`` (ADR-018) n'est **pas** imposée ici :
elle est garantie à la source par l'adapter baseline (qui lit ``identifier`` du
payload d'ingestion), et l'exiger casserait les cas jouets à ``doc_id`` plats
du scorer (ADR-028). On vérifie seulement le non-vide.
"""

from __future__ import annotations

from murphy_eval.core.models._base import Frozen
from murphy_eval.core.models.judgment import Qrels
from murphy_eval.core.models.run import Run


class Violation(Frozen):
    """Un invariant enfreint, localisé — de quoi tout rapporter d'un coup."""

    invariant: str
    query_id: str
    detail: str


class InvariantError(Exception):
    """Levée par un chargement *validant* quand un invariant est enfreint.

    Porte la liste complète des ``Violation`` : un artefact mal formé se
    diagnostique en une passe, pas violation après violation.
    """

    def __init__(self, violations: list[Violation]) -> None:
        self.violations = violations
        summary = "; ".join(
            f"[{v.invariant}] {v.query_id}: {v.detail}" for v in violations
        )
        super().__init__(f"{len(violations)} invariant(s) enfreint(s) — {summary}")


def _is_blank(value: str) -> bool:
    """Vide, tout-blanc, ou porteur d'un blanc de bord — un id qui n'en est pas un."""
    return value.strip() != value or not value.strip()


def check_run(run: Run) -> list[Violation]:
    """Tous les invariants de structure d'un run, collectés par requête.

    - ``ranks_contiguous`` : les rangs d'une requête forment ``1..n`` sans trou.
    - ``ranks_unique`` : aucun rang dupliqué dans une requête.
    - ``no_duplicate_chunk`` : pas de doublon ``(query_id, chunk_id)``.
    - ``consistent_chunk_doc`` : un ``chunk_id`` porte le *même* ``doc_id`` sur
      toute la requête. Un chunk rattaché à deux documents fausse en silence
      l'agrégation chunk→document (ADR-006). Contrôle propre au run : côté qrels,
      ``no_duplicate_chunk`` interdit déjà tout ``(query_id, chunk_id)`` répété,
      donc l'ambiguïté ne peut y naître.
    - ``well_formed_id`` : ``chunk_id`` et ``doc_id`` non vides, sans blanc de
      bord (forme canonique stricte non exigée — cf. docstring du module).
    """
    violations: list[Violation] = []
    for query_id, entries in run.by_query().items():
        ranks = [e.rank for e in entries]

        if len(set(ranks)) != len(ranks):
            dup_ranks = sorted({r for r in ranks if ranks.count(r) > 1})
            violations.append(
                Violation(
                    invariant="ranks_unique",
                    query_id=query_id,
                    detail=f"rang(s) dupliqué(s) : {dup_ranks}",
                )
            )
        elif sorted(ranks) != list(range(1, len(ranks) + 1)):
            violations.append(
                Violation(
                    invariant="ranks_contiguous",
                    query_id=query_id,
                    detail=f"rangs non contigus 1..{len(ranks)} : {sorted(ranks)}",
                )
            )

        chunk_ids = [e.chunk_id for e in entries]
        if len(set(chunk_ids)) != len(chunk_ids):
            dup_chunks = sorted({c for c in chunk_ids if chunk_ids.count(c) > 1})
            violations.append(
                Violation(
                    invariant="no_duplicate_chunk",
                    query_id=query_id,
                    detail=f"chunk_id dupliqué(s) dans la requête : {dup_chunks}",
                )
            )

        chunk_to_docs: dict[str, set[str]] = {}
        for entry in entries:
            chunk_to_docs.setdefault(entry.chunk_id, set()).add(entry.doc_id)
        ambiguous = sorted(c for c, docs in chunk_to_docs.items() if len(docs) > 1)
        if ambiguous:
            violations.append(
                Violation(
                    invariant="consistent_chunk_doc",
                    query_id=query_id,
                    detail=f"chunk_id rattaché à plusieurs doc_id : {ambiguous}",
                )
            )

        for entry in entries:
            if _is_blank(entry.doc_id) or _is_blank(entry.chunk_id):
                violations.append(
                    Violation(
                        invariant="well_formed_id",
                        query_id=query_id,
                        detail=(
                            f"id vide ou à blanc de bord : "
                            f"chunk_id={entry.chunk_id!r} doc_id={entry.doc_id!r}"
                        ),
                    )
                )
    return violations


def check_qrels(qrels: Qrels) -> list[Violation]:
    """Invariants de structure des qrels, collectés par requête.

    - ``no_duplicate_chunk`` : pas de jugement en double sur ``(query_id,
      chunk_id)`` (un même chunk jugé deux fois est une ambiguïté, pas une
      donnée).
    - ``well_formed_id`` : ``chunk_id`` et ``doc_id`` non vides, sans blanc.
    """
    violations: list[Violation] = []
    for query_id, judgments in qrels.by_query().items():
        chunk_ids = [j.chunk_id for j in judgments]
        if len(set(chunk_ids)) != len(chunk_ids):
            dupes = sorted({c for c in chunk_ids if chunk_ids.count(c) > 1})
            violations.append(
                Violation(
                    invariant="no_duplicate_chunk",
                    query_id=query_id,
                    detail=f"chunk_id jugé plusieurs fois : {dupes}",
                )
            )
        for judgment in judgments:
            if _is_blank(judgment.doc_id) or _is_blank(judgment.chunk_id):
                violations.append(
                    Violation(
                        invariant="well_formed_id",
                        query_id=query_id,
                        detail=(
                            f"id vide ou à blanc de bord : "
                            f"chunk_id={judgment.chunk_id!r} doc_id={judgment.doc_id!r}"
                        ),
                    )
                )
    return violations


def check_run_against_qrels(run: Run, qrels: Qrels) -> list[Violation]:
    """Invariant croisé run↔qrels : espaces de nommage ``doc_id`` compatibles.

    Garde-fou contre l'appariement muet : si un run est produit en ECLI et les
    qrels en ID DILA (ou l'inverse), l'intersection des ``doc_id`` est vide et
    **toutes les métriques valent 0** sans qu'aucune erreur ne soit levée — le
    pire des échecs, car il ressemble à un mauvais score légitime.

    On ne signale que lorsque les deux côtés d'une requête sont non vides mais
    **disjoints** : une requête sans jugement (ou sans hit) n'est pas une
    incohérence de nommage, juste une couverture partielle.
    """
    violations: list[Violation] = []
    run_docs = run.by_query()
    qrels_docs = qrels.by_query()
    for query_id in sorted(set(run_docs) & set(qrels_docs)):
        run_ids = {e.doc_id for e in run_docs[query_id]}
        qrels_ids = {j.doc_id for j in qrels_docs[query_id]}
        if run_ids and qrels_ids and run_ids.isdisjoint(qrels_ids):
            violations.append(
                Violation(
                    invariant="shared_id_namespace",
                    query_id=query_id,
                    detail=(
                        f"aucun doc_id commun entre run et qrels — espaces de "
                        f"nommage disjoints (run p.ex. {sorted(run_ids)[:2]}, "
                        f"qrels p.ex. {sorted(qrels_ids)[:2]})"
                    ),
                )
            )
    return violations
