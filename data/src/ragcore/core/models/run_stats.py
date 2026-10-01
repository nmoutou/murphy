"""RunStats — l'agrégat d'un run, MERGEABLE (monoïde de fusion, §11).

Avec N workers il n'y a plus *un* agrégateur mais N. Le verrou disparaît parce
que rien n'est partagé : chaque worker tient SON agrégat local, immuable, et le
pipeline les RÉDUIT. La fusion est une fonction pure — zéro section critique.
"""

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["RunStats"]


class RunStats(BaseModel):
    """Agrégat immuable et fusionnable des événements d'un run (ou d'un worker).

    Monoïde :
      - élément neutre : ``RunStats.empty()``
      - opérateur      : ``merge`` — associatif ET commutatif
      - lois           : ``merge(x, empty()) == merge(empty(), x) == x``
                         ``merge(merge(a, b), c) == merge(a, merge(b, c))``
                         ``merge(a, b) == merge(b, a)``

    La commutativité n'est pas un luxe, c'est une contrainte de correction : les
    workers finissent dans un ordre non déterministe. Une fusion non commutative
    ferait dépendre le RunSummary de l'ordonnancement — un non-déterminisme
    silencieux. Elle interdit donc tout champ du genre « le premier échec ».
    """

    model_config = ConfigDict(frozen=True)

    counts: dict[str, int] = Field(default_factory=dict)
    """event_type -> nombre d'occurrences. Fusion : somme."""

    unknowns: dict[str, list[str]] = Field(default_factory=dict)
    """Catégorie -> vocabulaire que le run n'a pas su nommer.

    C'est un ENSEMBLE, pas un compteur : « la balise ``foo`` est inconnue » est
    vraie une fois pour toutes. Deux workers qui rencontrent la même balise ne
    doivent pas la lister deux fois. Fusion : union dédupliquée, ordre stable.
    """

    @classmethod
    def empty(cls) -> "RunStats":
        """L'élément neutre du monoïde."""
        return cls()

    def merge(self, other: "RunStats") -> "RunStats":
        """Opérateur associatif et commutatif. Ne mute rien ; retourne un neuf."""
        counts = dict(self.counts)
        for event_type, n in other.counts.items():
            counts[event_type] = counts.get(event_type, 0) + n

        unknowns: dict[str, list[str]] = {
            category: list(values) for category, values in self.unknowns.items()
        }
        for category, values in other.unknowns.items():
            known = unknowns.setdefault(category, [])
            for value in values:
                if value not in known:
                    known.append(value)

        return RunStats(counts=counts, unknowns=unknowns)

    @classmethod
    def reduce(cls, stats: Iterable["RunStats"]) -> "RunStats":
        """Réduit N agrégats en un seul. ``reduce([])`` vaut ``empty()``."""
        result = cls.empty()
        for stat in stats:
            result = result.merge(stat)
        return result

    def with_count(self, event_type: str, n: int = 1) -> "RunStats":
        return self.merge(RunStats(counts={event_type: n}))

    def with_unknown(self, category: str, value: str) -> "RunStats":
        return self.merge(RunStats(unknowns={category: [value]}))
