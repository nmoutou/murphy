"""``WorkerBackends`` — les quatre backends d'un worker, chacun à sa place NOMMÉE.

Avant, ``RegistryAwareTelemetry`` recevait un ``dict[str, TelemetryPort]`` et
retrouvait ses backends par des clés-chaînes : ``self._backends["log"]``,
``self._backends.get("aggregate")`` suivi d'un ``isinstance``. §12 condamne cela
nommément : une clé-chaîne est un contrat que rien ne vérifie — une faute de frappe
(``"aggregat"``) ou un backend manquant ne se voit qu'à l'exécution, et le type de
l'agrégat doit être re-prouvé à chaque usage.

Ici, les quatre rôles sont des CHAMPS. Le ``behavior`` (``EventBehavior``, déjà
typé : ``log``/``track_jsonl``/``track_mongo``/``aggregate``) s'apparie un pour un
avec eux. Et ``aggregate`` est typé ``RunStatsAggregator``, pas ``TelemetryPort`` :
c'est LUI qui porte le ``RunStats`` du run, le seul à savoir ``snapshot``,
``record_unknown``, ``record_audit_failure``. Le typer fort supprime tout garde
``isinstance`` en aval — le compilateur garantit ce que le code vérifiait à la main.

L'ordre de fermeture est une propriété de CE type, pas de son consommateur :
l'agrégat se ferme EN DERNIER, sans quoi il ne serait plus là pour compter l'échec
de fermeture des trois autres. ``closable_in_order`` le grave ici, une fois.
"""

from dataclasses import dataclass

from ragcore.core.ports.telemetry import TelemetryPort

from .aggregator import RunStatsAggregator

__all__ = ["WorkerBackends"]


@dataclass(frozen=True)
class WorkerBackends:
    """Les quatre backends d'une pile de worker, appariés aux champs d'``EventBehavior``.

    ``log``/``jsonl``/``mongo`` sont des ``TelemetryPort`` interchangeables (un
    ``NoopTelemetry`` remplace ``mongo`` en mode local). ``aggregate`` est un
    ``RunStatsAggregator`` concret : il est le porteur du bilan, pas un simple
    récepteur d'événements.
    """

    log: TelemetryPort
    jsonl: TelemetryPort
    mongo: TelemetryPort
    aggregate: RunStatsAggregator

    def closable_in_order(self) -> list[tuple[str, TelemetryPort]]:
        """Les backends à fermer, ``aggregate`` en DERNIER.

        Le nom accompagne chaque backend : il sert à imputer un échec de fermeture
        (``record_audit_failure(name)``). L'agrégat ferme en dernier parce qu'il est
        le seul à pouvoir enregistrer la mort des autres — le fermer d'abord, ce
        serait perdre le compte des pertes qui suivent.
        """
        return [
            ("log", self.log),
            ("jsonl", self.jsonl),
            ("mongo", self.mongo),
            ("aggregate", self.aggregate),
        ]
