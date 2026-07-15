"""DrainReport — ce que le drain a VU, pas seulement ce qu'il a fait.

``AsyncRuntime.close()`` drainait les écritures d'audit en vol avec
``gather(..., return_exceptions=True)`` — et **jetait le résultat**. Or
``return_exceptions=True`` ne veut pas dire « il n'y aura pas d'exception », il veut
dire « rends-les moi dans la liste au lieu de lever ». Cette liste partait à la
poubelle : une écriture d'audit qui échouait ne produisait *rien du tout*, pas même
un log.

C'était le plus silencieux des trous, et le pire placé : le chemin async (saga,
workers) porte l'essentiel du volume.

Le runtime reste **bête** — il ne connaît pas la télémétrie et ne doit pas la
connaître. Il *rend un compte* ; c'est son appelant, qui tient la pile de télémétrie,
qui traduit ce compte en ``audit.write.failed``.
"""

from pydantic import BaseModel, ConfigDict

__all__ = ["DrainReport"]


class DrainReport(BaseModel):
    """Le bilan d'un drain : combien de tâches attendues, combien ont levé."""

    model_config = ConfigDict(frozen=True)

    drained: int = 0
    """Tâches en vol qui ont été attendues (échouées comprises)."""

    failed: int = 0
    """Tâches qui ont levé. Non nul = des écritures d'audit sont PERDUES."""

    @classmethod
    def empty(cls) -> "DrainReport":
        """Rien n'était en vol — le cas nominal d'un runtime déjà au repos."""
        return cls()
