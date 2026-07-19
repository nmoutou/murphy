"""Chargement des qrels/runs — canonique JSONL (primaire) et TREC plat (projection).

ADR-008 : le JSONL est la **seule source de vérité** ; la forme TREC plate
(``query_id 0 chunk_id grade`` pour les qrels, ``query_id Q0 chunk_id rank
score run_tag`` pour les runs) n'est qu'une **projection déterministe**,
utile pour l'outillage standard et pour le cross-check `trec_eval` (oracle
secondaire, ADR-028).

Les deux formes de chargement produisent les **mêmes modèles de domaine**
(``Qrels``/``Run``). La forme TREC plate est structurellement moins riche
(pas de provenance, pas de q1–q3, et pour les runs, pas de ``doc_id`` — d'où
le résolveur, couture explicite pour B-05, cf. ``core/models/run.py``).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from murphy_eval.core.models.judgment import Judgment, Qrels
from murphy_eval.core.models.run import Run, RunEntry


def load_jsonl_qrels(path: Path) -> Qrels:
    """Charge le fichier qrels canonique (ADR-008), un ``Judgment`` par ligne."""
    judgments = tuple(
        Judgment.model_validate(json.loads(line)) for line in _non_empty_lines(path)
    )
    return Qrels(judgments=judgments)


def load_jsonl_run(path: Path) -> Run:
    """Charge un run canonique JSONL, portant directement ``doc_id`` par chunk."""
    entries = tuple(
        RunEntry.model_validate(json.loads(line)) for line in _non_empty_lines(path)
    )
    return Run(entries=entries)


def dump_jsonl_run(run: Run, path: Path) -> None:
    """Écrit un run canonique JSONL (ADR-008), une ligne ``RunEntry`` par chunk.

    Writer symétrique de ``load_jsonl_run`` au niveau des **entrées** : seules
    les ``RunEntry`` sont persistées (une par ligne), donc ``dump`` puis ``load``
    redonne les mêmes ``entries``. ``Run.run_tag`` n'est **pas** écrit (le JSONL
    n'a pas de ligne d'en-tête) ; il reste reconstructible depuis les entrées, où
    ``RunEntry.run_tag`` le porte déjà de façon redondante. C'est la sortie de
    production de B-05 — un run **immuable** (ADR-008), archivé, relu tel quel.

    Déterministe : les entrées sont sérialisées dans leur ordre d'apparition
    (l'ordre porte déjà le rang) ; ``model_dump`` fige l'ordre des clés. Deux
    ``dump`` du même ``Run`` produisent des octets identiques.
    """
    lines = (
        json.dumps(entry.model_dump(), ensure_ascii=False, separators=(",", ":"))
        for entry in run.entries
    )
    path.write_text("".join(f"{line}\n" for line in lines))


def load_trec_qrels(path: Path) -> Qrels:
    """Charge des qrels TREC plats : ``query_id 0 chunk_id grade``.

    Forme structurellement dégradée par rapport au JSONL canonique :
    ``doc_id`` est reconstitué en réutilisant ``chunk_id`` (impossible à
    séparer sans convention externe), et la provenance (q1–q3, annotateur…)
    est absente. À réserver au chargement de fixtures/outillage externe, pas
    au flux de production (qui charge le JSONL canonique).
    """
    judgments = []
    for line in _non_empty_lines(path):
        query_id, _iteration, chunk_id, grade = line.split()
        judgments.append(
            Judgment(
                query_id=query_id,
                doc_id=chunk_id,
                chunk_id=chunk_id,
                grade=int(grade),
            )
        )
    return Qrels(judgments=tuple(judgments))


def load_trec_run(path: Path, resolve_doc_id: Callable[[str], str]) -> Run:
    """Charge un run TREC plat : ``query_id Q0 chunk_id rank score run_tag``.

    Une ligne TREC ne porte que ``chunk_id`` : ``resolve_doc_id`` est le
    résolveur explicite qui reconstitue le ``doc_id`` parent (couture pour
    B-05 — en production, B-05 émet des runs JSONL canoniques qui portent
    déjà ``doc_id``, ce loader ne sert qu'à des runs TREC produits hors de P2).
    """
    entries = []
    for line in _non_empty_lines(path):
        query_id, _q0, chunk_id, rank, score, run_tag = line.split()
        entries.append(
            RunEntry(
                query_id=query_id,
                chunk_id=chunk_id,
                doc_id=resolve_doc_id(chunk_id),
                rank=int(rank),
                score=float(score),
                run_tag=run_tag,
            )
        )
    return Run(entries=tuple(entries))


def _non_empty_lines(path: Path) -> list[str]:
    return [line for line in path.read_text().splitlines() if line.strip()]
