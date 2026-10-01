"""``WorkerBackends`` — les backends d'un worker, chacun à sa place NOMMÉE.

Avant, ``RegistryAwareTelemetry`` recevait un ``dict[str, TelemetryPort]`` et
retrouvait ses backends par des clés-chaînes : ``self._backends["log"]``,
``self._backends.get("aggregate")`` suivi d'un ``isinstance``. §12 condamne cela
nommément : une clé-chaîne est un contrat que rien ne vérifie — une faute de frappe
(``"aggregat"``) ou un backend manquant ne se voit qu'à l'exécution, et le type de
l'agrégat doit être re-prouvé à chaque usage.

Ici, les rôles sont des CHAMPS. ``log`` sert les logs textuels (``log()``) ;
``aggregate`` reçoit les événements que le ``behavior`` (``EventBehavior``) lui route.
Et ``aggregate`` est typé
``RunStatsAggregator``, pas ``TelemetryPort`` : c'est LUI qui porte le ``RunStats`` du
run, le seul à savoir ``snapshot`` et ``record_unknown``. Le typer fort supprime tout
garde ``isinstance`` en aval — le compilateur garantit ce que le code vérifiait à la
main.

Brancher un nouvel outil, c'est ajouter un champ ici et une colonne au behavior.
"""

from dataclasses import dataclass

from ragcore.core.ports.telemetry import TelemetryPort

from .aggregator import RunStatsAggregator

__all__ = ["WorkerBackends"]


@dataclass(frozen=True)
class WorkerBackends:
    """Les backends d'une pile de worker, appariés aux champs d'``EventBehavior``.

    ``log`` est un ``TelemetryPort`` interchangeable. ``aggregate`` est un
    ``RunStatsAggregator`` concret : il est le porteur du bilan, pas un simple
    récepteur d'événements.
    """

    log: TelemetryPort
    aggregate: RunStatsAggregator

    def closable_in_order(self) -> list[tuple[str, TelemetryPort]]:
        """Les backends à fermer, ``aggregate`` en DERNIER.

        Le nom accompagne chaque backend : il nomme un échec de fermeture dans les
        logs. L'agrégat ferme en dernier : c'est lui qui rend le bilan, il doit
        survivre aux autres.
        """
        return [
            ("log", self.log),
            ("aggregate", self.aggregate),
        ]
