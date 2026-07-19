"""Socle commun des modèles de domaine — gelé et fermé aux extras.

Tous les modèles de ``core/models`` héritent de ``Frozen`` : immuables
(``frozen=True``) et refusant tout champ non déclaré (``extra="forbid"``).
Une seule définition de la config pydantic pour tout le domaine — un ajout
futur (``validate_assignment``, ``json_schema_extra``…) se fait ici, jamais
recopié dans quatre fichiers où il divergerait à bas bruit.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
