"""``murphy-eval-cocitation`` — produit le jeu de paires de co-citation (B-07).

Le composeur du socle de strate 2 : il relie ce qui existait déjà sans se relier.

    settings → Neo4jCocitationMiner → mine_pairs → dump_jsonl_pairs
                                                 → summarize_pairs → summary.json

**Pourquoi une commande.** E-P2-05 exige un jeu de paires *versionné*, avec
volumétrie et méthode documentées, et E-T-02 une procédure de rejeu. Tant que
produire le jeu demandait d'écrire du Python à la main, aucune des deux n'était
satisfaite : la volumétrie n'était jamais mesurée et B-09 n'avait rien à
consommer. Cette commande *est* la procédure de rejeu.

**Ce qu'elle n'est pas.** Elle ne juge rien. ADR-029 a rétrogradé la strate 2 en
diagnostic précision-seulement : la sortie est un fait mécanique du graphe (des
arêtes), jamais un grade, jamais des qrels. Le résumé de volumétrie est
descriptif — pas une métrique.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from murphy_eval.adapters.cocitation_io import dump_jsonl_pairs
from murphy_eval.adapters.graph.neo4j_cocitation import Neo4jCocitationMiner
from murphy_eval.adapters.settings import get_eval_infra_settings
from murphy_eval.core.ports.graph import CocitationMiner
from murphy_eval.core.services.cocitation_report import (
    CocitationSummary,
    summarize_pairs,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
"""La racine de ``eval/`` (``src/murphy_eval/cli/`` en est à trois niveaux).

Calculée depuis ``__file__``, **jamais depuis le CWD** — même discipline que
``ROOT_ENV_FILE`` : l'artefact doit atterrir au même endroit quel que soit le
répertoire depuis lequel on lance la commande, sans quoi « versionné » n'a
pas de sens."""

DEFAULT_OUT_DIR = PROJECT_ROOT / "artifacts" / "cocitation"
"""Les artefacts de co-citation sont **commités** (E-P2-05 : jeu versionné) —
ce n'est pas un répertoire de travail jetable."""

EMPTY_RESULT_HINT = (
    "Aucune paire minée : le tenant demandé n'existe peut-être pas dans le graphe "
    "(l'ingestion écrit `OWNER_ID` du .env.dev), ou le graphe n'est pas peuplé."
)
"""Un jeu vide n'est **pas** une erreur — mais c'est presque toujours un symptôme.

Mesuré : la première version de cette commande codait ``"system"`` en dur alors que
l'ingestion écrit ``"default"``. Elle produisait un artefact vide, en code 0, sans
rien signaler. On avertit donc explicitement plutôt que de laisser un fichier vide
passer pour un résultat."""

PAIRS_FILENAME = "pairs.jsonl"
SUMMARY_FILENAME = "summary.json"


def build_miner() -> Neo4jCocitationMiner:
    """Construit le miner réel depuis l'environnement (``.env.dev`` racine).

    Isolé dans une fabrique pour que ``run`` reste testable sans réseau : les
    tests injectent une doublure du port ``CocitationMiner`` au lieu de
    monkeypatcher le driver Neo4j.
    """
    settings = get_eval_infra_settings()
    return Neo4jCocitationMiner(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password.get_secret_value()),
    )


def run(miner: CocitationMiner, *, owner_id: str, out_dir: Path) -> CocitationSummary:
    """Mine, écrit les deux artefacts, rend la volumétrie.

    Ne ferme pas le miner : la durée de vie de la connexion appartient à
    l'appelant qui l'a ouverte (cf. ``main``).
    """
    pairs = miner.mine_pairs(owner_id=owner_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    dump_jsonl_pairs(pairs, out_dir / PAIRS_FILENAME)
    summary = summarize_pairs(pairs)
    _dump_summary(summary, out_dir / SUMMARY_FILENAME)
    return summary


def _dump_summary(summary: CocitationSummary, path: Path) -> None:
    """Archive la volumétrie — c'est la *preuve* d'E-P2-05, pas un affichage.

    ``model_dump_json`` fige l'ordre des clés (pydantic), donc deux runs sur le
    même graphe produisent des octets identiques, comme le JSONL des paires.
    """
    path.write_text(f"{summary.model_dump_json(indent=2)}\n", encoding="utf-8")


def _format_summary(
    summary: CocitationSummary, pairs_path: Path, *, owner_id: str
) -> str:
    """Le même contenu que ``summary.json``, mis en forme pour un humain.

    Le tenant est affiché : sans lui, un jeu vide est indiagnosticable.
    """
    lines = [
        f"tenant « {owner_id} » — {summary.pair_count} paires · "
        f"{summary.document_count} documents distincts",
        f"→ {pairs_path}",
    ]
    lines.extend(f"  {verb:<16} {count}" for verb, count in summary.pairs_by_verb)
    return "\n".join(lines)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="murphy-eval-cocitation",
        description=(
            "Mine les paires de co-citation (strate 2, ADR-029) depuis le graphe "
            "Neo4j et écrit un jeu versionné + sa volumétrie. Diagnostic "
            "précision-seulement : ce ne sont PAS des qrels."
        ),
    )
    parser.add_argument(
        "--owner-id",
        default=None,
        help="Tenant à miner (défaut : OWNER_ID du .env.dev, comme l'ingestion).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Répertoire des artefacts (défaut : {DEFAULT_OUT_DIR}).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Point d'entrée. Rend ``0`` en succès, ``1`` sur incident d'exploitation.

    Les échecs attendus — Neo4j injoignable, ``.env.dev`` incomplet, graphe
    incohérent avec le contrat d'ingestion (``ValueError`` du fail-fast de
    ``_record_to_pair``) — sortent en message sur ``stderr``, **sans traceback** :
    ce sont des conditions d'environnement à corriger, pas des bugs à rapporter.
    """
    args = _parse_args(argv)

    try:
        owner_id = args.owner_id or get_eval_infra_settings().owner_id
        miner = build_miner()
    except Exception as exc:  # noqa: BLE001 - frontière CLI : tout échec = code 1
        print(f"Impossible de se connecter au graphe : {exc}", file=sys.stderr)
        return 1

    try:
        summary = run(miner, owner_id=owner_id, out_dir=args.out_dir)
    except Exception as exc:  # noqa: BLE001 - idem, y compris le fail-fast métier
        print(f"Échec du minage : {exc}", file=sys.stderr)
        return 1
    finally:
        miner.close()

    print(_format_summary(summary, args.out_dir / PAIRS_FILENAME, owner_id=owner_id))
    if summary.pair_count == 0:
        print(EMPTY_RESULT_HINT, file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
