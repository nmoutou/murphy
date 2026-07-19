"""``EvalInfraSettings`` — l'infrastructure lue de l'environnement.

Comme côté ingestion (``ragcore/adapters/config/settings.py``), **rien ici
n'entre dans l'identité des vecteurs ni dans le nom de collection** : ce sont
des URLs, des noms de base et des secrets, pas des leviers de qualité de
récupération (ceux-là vivent dans ``W``, hors de ce projet). Cette scission est
l'invariant même d'ADR-027.

**Le fichier lu est celui de la RACINE** (``ROOT_ENV_FILE``), jamais un ``.env``
local à ``eval/`` — il n'y en a pas, et en créer un n'aurait aucun effet
(CLAUDE.md : un seul fichier d'environnement pour tout le système, pour que le
conteneur TEI et le harnais ne puissent jamais diverger sur le modèle
d'embedding). Le chemin est calculé depuis ``__file__``, jamais depuis le CWD.

Les noms de variables sont ceux du ``.env.dev`` réel, partagés avec l'ingestion
(``MONGODB_META_DB_NAME``, ``QDRANT_URL``…) — on lit la même vérité, on ne la
réinvente pas.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_FILE = Path(__file__).resolve().parents[4] / ".env.dev"
"""Le seul fichier d'environnement du projet : la racine (``eval/`` en est un
sous-dossier direct, d'où ``parents[4]``)."""


class EvalInfraSettings(BaseSettings):
    """Config d'infra du harnais : Qdrant, Mongo (méta), service d'embedding."""

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE, extra="ignore", case_sensitive=False
    )

    qdrant_url: str = Field(alias="QDRANT_URL")
    qdrant_api_key: SecretStr | None = Field(default=None, alias="QDRANT_API_KEY")

    mongodb_uri: str = Field(alias="MONGODB_URI")
    mongodb_meta_db_name: str = Field(
        default="MURPHY_META", alias="MONGODB_META_DB_NAME"
    )

    embedding_service_url: str = Field(alias="EMBEDDING_SERVICE_URL")
    embedding_model: str = Field(alias="EMBEDDING_MODEL")
    embedding_api_key: SecretStr | None = Field(default=None, alias="EMBEDDING_API_KEY")


@lru_cache
def get_eval_infra_settings() -> EvalInfraSettings:
    """L'instance unique — lue une fois, réutilisée (comme ``get_infra_settings``)."""
    return EvalInfraSettings()
