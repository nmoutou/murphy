"""La configuration d'infrastructure, lue de l'environnement, jamais du dépôt : bases,
secrets, chemins, modèle d'embedding et découpe.

Les secrets sont des ``SecretStr`` : un ``str`` finirait dans un log le jour où
quelqu'un journalise l'objet entier.

Deux bases Mongo : les données d'un côté, la méta (audit, bilans, pendantes) de
l'autre, qu'un ``drop`` des données n'emporte jamais.

Le pipeline tourne sur l'hôte, les bases en conteneur : le fichier porte les URLs côté
hôte (``localhost``), et docker-compose les surcharge pour les services conteneurisés.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ragcore.core.models.processing import ChunkingConfig

__all__ = [
    "ChunkingSettings",
    "EmbeddingRuntimeSettings",
    "Environment",
    "InfraSettings",
    "LogLevel",
    "LoggingSettings",
    "get_chunking_config",
    "get_embedding_runtime_settings",
    "get_infra_settings",
    "get_log_level",
]


ROOT_ENV_FILE = Path(__file__).resolve().parents[5] / ".env.dev"
"""Le seul fichier d'environnement du projet, à la racine du dépôt.

Calculé depuis ``__file__``, jamais depuis le CWD : un ``kedro run`` lancé d'ailleurs ne
lirait sinon aucun fichier, en silence.
"""

Environment = Literal["dev", "prod"]
"""Tout ce qui n'est pas un poste de dev est ``prod``."""

DEFAULT_ENVIRONMENT: Environment = "prod"

LogLevel = Literal["debug", "info", "warning", "error", "critical"]
"""Les niveaux de ``logging``, en minuscules."""

DEFAULT_LOG_LEVEL: LogLevel = "info"

DEFAULT_EMBEDDING_INGESTION_TIMEOUT_MS = 120_000
"""Deux minutes : les lots d'un document partent ensemble et font la queue côté GPU."""


def _require_env_file() -> Path:
    """Vérifié à la lecture, jamais à l'import : les tests unitaires tournent sans
    ``.env.dev``. Son absence est fatale, jamais rattrapée par les défauts.
    """
    if not ROOT_ENV_FILE.exists():
        raise FileNotFoundError(
            f"Aucun fichier d'environnement à {ROOT_ENV_FILE}.\n"
            f"Il est UNIQUE et vit à la RACINE du dépôt — il n'y en a pas dans `data/`, "
            f"et en créer un ici n'aurait aucun effet.\n"
            f"    cp .env.example .env.dev   (depuis la racine), puis renseigner les secrets."
        )
    return ROOT_ENV_FILE


class InfraSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, extra="ignore")

    environment: Environment = DEFAULT_ENVIRONMENT
    """Seul `dev` applique `parameters.yml`, dont `nuke_all` qui efface toutes les bases.
    Le défaut est donc `prod` : oublier la variable ne doit jamais vider une prod. Toute
    autre valeur arrête le run ; vide, la variable vaut absente."""

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_data_db_name: str = "MURPHY_DATA"
    mongodb_meta_db_name: str = "MURPHY_META"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("neo4j")

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str
    """Sans défaut. Le backend lit la même variable : l'ingestion écrit la collection
    qu'il interroge."""

    xml_source_path: Path = Path("/mnt/data/Murphy/src")
    """La racine du corpus, en chemin absolu hors du dépôt. Le sous-répertoire de chaque
    source vit dans `sources/registry.py`."""

    source: str = "all"
    """`all` = toutes les sources ingérables. Surchargeable : `kedro run --params
    source=cass,jade`."""

    @field_validator("environment", mode="before")
    @classmethod
    def _environnement_vide_vaut_absent(cls, value: object) -> object:
        """``ENVIRONMENT=`` produit ``''`` : l'absence, pas une coquille."""
        return DEFAULT_ENVIRONMENT if value == "" else value

    @field_validator("qdrant_api_key", mode="after")
    @classmethod
    def _secret_vide_vaut_absent(cls, value: SecretStr | None) -> SecretStr | None:
        """``QDRANT_API_KEY=`` produit ``SecretStr('')``, pas ``None`` : le client
        enverrait une clé vide et serait refusé."""
        if value is not None and not value.get_secret_value():
            return None
        return value


class EmbeddingRuntimeSettings(BaseSettings):
    """Le service TEI : le modèle qu'il doit servir, et comment le joindre. La dimension
    est mesurée au démarrage (``served_model.inspect_served_model``).
    """

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE, env_prefix="embedding_", extra="ignore"
    )

    model: str = Field(min_length=1)
    """Celui que TEI charge et que le backend interroge."""
    service_url: str = Field(min_length=1)
    """L'API compatible OpenAI de TEI, p. ex. ``http://localhost:5001/v1``. Aucun défaut
    ne doit désigner un service."""
    batch_size: int = 32
    ingestion_timeout: int = Field(default=DEFAULT_EMBEDDING_INGESTION_TIMEOUT_MS, gt=0)
    """En millisecondes. Plus long que celui du backend : l'ingestion envoie des lots en
    parallèle."""


class ChunkingSettings(BaseSettings):
    """La découpe, en caractères, sans défaut : en changer invalide les vecteurs écrits.
    Les chaînes de l'environnement sont converties ici, validées par ``ChunkingConfig``.
    """

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE, env_prefix="chunking_", extra="ignore"
    )

    max_chars: int
    overlap_chars: int

    def to_config(self) -> ChunkingConfig:
        """Bornée : ``0 ≤ overlap_chars < max_chars``."""
        return ChunkingConfig(
            max_chars=self.max_chars, overlap_chars=self.overlap_chars
        )


class LoggingSettings(BaseSettings):
    """Le niveau des loggers ``kedro``, ``data`` et ``ragcore`` ; les bibliothèques
    tierces restent en ``WARNING``. Une valeur inconnue arrête le run ; vide, la variable
    vaut absente.
    """

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE, env_prefix="kedro_", extra="ignore"
    )

    log_level: LogLevel = DEFAULT_LOG_LEVEL

    @field_validator("log_level", mode="before")
    @classmethod
    def _niveau_vide_vaut_absent(cls, value: object) -> object:
        """``KEDRO_LOG_LEVEL=`` produit ``''`` : l'absence."""
        return DEFAULT_LOG_LEVEL if value == "" else value


@lru_cache
def get_infra_settings() -> InfraSettings:
    _require_env_file()
    return InfraSettings()


@lru_cache
def get_embedding_runtime_settings() -> EmbeddingRuntimeSettings:
    _require_env_file()
    return EmbeddingRuntimeSettings()


@lru_cache
def get_chunking_config() -> ChunkingConfig:
    _require_env_file()
    return ChunkingSettings().to_config()


@lru_cache
def get_log_level() -> LogLevel:
    _require_env_file()
    return LoggingSettings().log_level
