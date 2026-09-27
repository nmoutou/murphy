"""Adaptateur de télémétrie qui dispatche selon un registry par event_type.

Implémente le port TelemetryPort avec un routage granulaire.
"""

import logging
from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.models.run_stats import RunStats
from ragcore.core.services.telemetry_registry import TelemetryRegistry

from .worker_backends import WorkerBackends

_LOGGER = logging.getLogger(__name__)


class RegistryAwareTelemetry:
    """Fan-out guidé par un TelemetryRegistry — la pile de télémétrie d'UN worker.

    Dispatche chaque emit() vers les 4 backends selon le behavior_for(event_type).
    Les exceptions des delegates sont isolées (best-effort) : la télémétrie observe
    l'ingestion, elle ne la fait jamais échouer. Isolées, mais **comptées** : un
    backend qui rate son écriture émarge à ``audit.write.failed``, donc au bilan du
    run — ne pas casser l'ingestion n'autorise pas à taire la perte.

    Satisfait ``WorkerTelemetry`` : au-delà du fan-out, elle sait rendre son agrégat
    local (``snapshot``) et fermer ses backends (``close``). Sans cela le pool ne
    pourrait pas la consommer — un fan-out qui ne sait pas se réduire n'est pas une
    pile de worker, c'est un tuyau.

    Les backends sont un ``WorkerBackends`` typé (§12) : plus de clés-chaînes, plus
    de garde ``isinstance`` sur l'agrégat — chaque rôle est un champ, et ``aggregate``
    EST un ``RunStatsAggregator`` par construction.
    """

    def __init__(
        self,
        registry: TelemetryRegistry,
        backends: WorkerBackends,
    ):
        """
        Args:
            registry: TelemetryRegistry qui map event_type → EventBehavior
            backends: WorkerBackends — les 4 rôles (log/jsonl/mongo/aggregate) wirés
                en amont. ``aggregate`` porte le RunStats que snapshot() rend au pool.
        """
        self._registry = registry
        self._backends = backends

    def emit(self, event: AuditEvent) -> None:
        """Dispatche vers les backends selon le EventBehavior.

        Le `event_type` est préservé tel quel — le registry contrôle le routage,
        pas le contenu. L'appariement est un pour un avec les champs du behavior :
        ``log``→``log``, ``track_jsonl``→``jsonl``, ``track_mongo``→``mongo``,
        ``aggregate``→``aggregate``.

        Un backend qui lève ne fait pas tomber les autres, et ne fait pas tomber
        l'ingestion — mais il est désormais COMPTÉ (cf. ``_deliver``).
        """
        behavior = self._registry.behavior_for(event.event_type)

        if behavior.log:
            self._deliver("log", self._backends.log, event)
        if behavior.track_jsonl:
            self._deliver("jsonl", self._backends.jsonl, event)
        if behavior.track_mongo:
            self._deliver("mongo", self._backends.mongo, event)
        if behavior.aggregate:
            self._deliver("aggregate", self._backends.aggregate, event)

    def _deliver(self, name: str, backend: Any, event: AuditEvent) -> None:
        """Un backend, une livraison, et un échec qui SE COMPTE.

        L'isolement des exceptions n'est pas négociable : la télémétrie observe
        l'ingestion, elle ne la fait jamais échouer. Mais isoler n'est pas oublier —
        ce code se contentait d'un ``_LOGGER.warning``, donc l'échec existait dans la
        console et nulle part dans le bilan. Un run pouvait perdre des lignes d'audit
        et se déclarer complet, sur des compteurs dont une partie n'était jamais
        arrivée en base.
        """
        try:
            backend.emit(event)
        except Exception as exc:  # noqa: BLE001 — frontière de télémétrie : un backend en panne ne casse pas le run, l'échec est compté (record_audit_failure)
            _LOGGER.warning(
                "telemetry backend '%s' error on %s: %s", name, event.event_type, exc
            )
            self.record_audit_failure(name)

    def log(self, level: str, message: str, **context: Any) -> None:
        """Passe-plat vers le backend log.

        .log() n'est pas filtré par le registry — toujours émis.

        Pas de ``record_audit_failure`` ici, et c'est délibéré : un log textuel n'est
        pas une ligne d'audit. Le perdre ne rend aucun compteur faux — donc ça ne
        dégrade pas le run.
        """
        try:
            self._backends.log.log(level, message, **context)
        except Exception as exc:  # noqa: BLE001 — frontière de télémétrie : un log textuel perdu ne fausse aucun compteur, il ne casse pas le run
            _LOGGER.warning("telemetry backend 'log' error on log(): %s", exc)

    def record_unknown(self, category: str, value: str) -> None:
        """Un vocabulaire non reconnu se déclare — il ne se jette pas en silence.

        Va droit à l'agrégat : un inconnu n'est pas un événement d'audit, c'est un
        aveu d'ignorance que le bilan du run doit porter (``RunStats.unknowns``).
        """
        self._backends.aggregate.record_unknown(category, value)

    def record_audit_failure(self, backend: str, n: int = 1) -> None:
        """Compte une écriture d'audit perdue — sans jamais la réémettre.

        Droit à l'agrégat, comme ``record_unknown``, et pour une raison plus forte
        encore : repasser par ``emit`` ferait ré-écrire les backends qui viennent de
        rater. Au mieux ils rateraient encore, au pire la récursion serait infinie.
        Un compteur en mémoire, lui, ne peut pas échouer sur du réseau.
        """
        self._backends.aggregate.record_audit_failure(backend, n)

    def snapshot(self) -> RunStats:
        """L'agrégat local de ce worker, à fusionner avec celui des autres."""
        return self._backends.aggregate.snapshot()

    def close(self) -> None:
        """Ferme les backends de ce worker. Un backend qui refuse de mourir ne doit
        pas empêcher les autres de le faire — mais il ne meurt plus en silence.

        Une fermeture qui échoue est une PERTE : c'est là qu'un fichier se vide sur
        disque, qu'un buffer part à la poubelle. Elle se compte donc comme un échec
        d'écriture, au même titre qu'un ``emit`` raté.

        L'ordre compte : l'agrégat est fermé **en dernier** (``closable_in_order``),
        sans quoi il ne serait plus là pour enregistrer les échecs de ceux qui le
        suivent. En pratique son ``close()`` ne fait rien (l'agrégat vit en mémoire) —
        mais s'en remettre à ça, c'est dépendre du détail d'implémentation d'un autre
        module.
        """
        for name, backend in self._backends.closable_in_order():
            closer = getattr(backend, "close", None)
            if closer is None:
                continue
            try:
                closer()
            except Exception as exc:  # noqa: BLE001 — frontière de télémétrie : un close() raté ne doit pas empêcher de fermer les backends suivants ; l'échec est compté
                _LOGGER.warning(
                    "telemetry backend '%s' error on close(): %s", name, exc
                )
                self.record_audit_failure(name)
