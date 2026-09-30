"""``InfraSettings`` — lue de l'environnement, jamais du dépôt.

Les bases, les secrets, les chemins : le *où* du pipeline. Les réglages du traitement
(découpe, modèle d'embedding) vivent dans ``conf/base/parameters.yml``.

La forme de ces modèles est **dictée par ses appelants**. ``orchestration/kedro/stores.py`` appelle
``.get_secret_value()`` sur le mot de passe Neo4j et la clé Qdrant : ce sont donc des
``SecretStr``, et le typage l'impose au lieu de l'espérer. Un secret qui traîne en
``str`` finit dans un log le jour où quelqu'un journalise l'objet entier.

Deux bases Mongo, et la distinction est structurelle : les *données* (documents,
chunks, manifest) vivent dans l'une, la *méta* (audit, bilans de run, pendantes) dans
l'autre. Un ``drop`` de la base de données ne doit jamais emporter la mémoire de ce
qu'on a fait.

**Le fichier lu est celui de la RACINE** (``ROOT_ENV_FILE``), pas un ``.env`` local — il
n'y en a pas dans ``data/``, et en créer un n'aurait aucun effet. Le pipeline tourne sur
l'*hôte* tandis que les bases tournent en *conteneur* : le fichier porte donc les URLs
côté hôte (``localhost``), et c'est ``docker-compose`` qui surcharge les services
conteneurisés avec leurs noms de service. Une variable ne peut pas valoir ``localhost``
et ``mongo`` à la fois ; l'hôte est celui qu'on ne peut pas surcharger, donc c'est lui
qui parle dans le fichier.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = [
    "EmbeddingRuntimeSettings",
    "InfraSettings",
    "get_embedding_runtime_settings",
    "get_infra_settings",
]


ROOT_ENV_FILE = Path(__file__).resolve().parents[5] / ".env.dev"
"""Le **seul** fichier d'environnement du projet : celui de la racine, pas d'ici.

``data/`` est un sous-module ; la racine est son parent (d'où ``parents[5]``). Le chemin
est calculé depuis ``__file__``, **jamais depuis le CWD** — un ``env_file=".env"`` relatif
se résout contre le répertoire courant, donc un ``kedro run`` lancé d'ailleurs que de
``data/`` ne lirait *aucun* fichier et prendrait **silencieusement tous les défauts**,
dont ``provider="noop"`` : des vecteurs nuls écrits dans la collection du vrai modèle.

Un seul fichier, deux consommateurs : le modèle que sert le conteneur TEI et celui que le
pipeline croit embarquer ne peuvent plus diverger, **parce qu'ils ne sont plus deux
variables**.
"""


def _require_env_file() -> Path:
    """Exige le fichier — à l'**instanciation**, jamais à l'import.

    Le vérifier au niveau module ferait échouer ``import ragcore`` sur une machine sans
    ``.env.dev`` : les tests unitaires, qui ne touchent aucune base et n'ont aucun besoin
    de configuration, ne s'importeraient plus. Le garde doit protéger ceux qui *lisent* la
    config, pas ceux qui importent le module qui la déclare.

    Son absence est **fatale** : la rattraper par les défauts est exactement la
    dégradation silencieuse que la doctrine proscrit.
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
    """Les bases, les chemins. Le *où*, jamais le *quoi*."""

    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, extra="ignore")

    environment: str = "prod"
    """L'environnement d'exécution. **Le défaut est `prod`, et c'est délibéré.**

    Il ne sert qu'à *une* chose : garder le mode `nuke_all` (voir
    `nodes/nuke_all.py`), qui efface TOUTES les données de TOUTES les bases, du seul
    environnement où l'effacement est sans conséquence. Le node refuse de tourner si
    `environment != "dev"`.

    Le défaut penche vers le refus, pas vers l'autorisation : un `.env` sans
    `ENVIRONMENT` est traité comme de la prod, donc protégé. Un garde-fou dont le
    défaut *ouvre* la trappe ne protège rien — il suffirait d'oublier une variable
    pour vider une prod. On rend l'effacement accidentel impossible, pas déconseillé."""

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_data_db_name: str = "LEGIFRANCE"
    mongodb_meta_db_name: str = "MURPHY_META"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("neo4j")

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str
    """Le nom de la collection Qdrant : fixe, et **sans défaut**.

    Le backend lit la même variable (``QDRANT_COLLECTION``) dans le même fichier :
    l'ingestion écrit la collection qu'il interroge. Absente, le run s'arrête au
    chargement de la configuration."""

    xml_source_path: Path = Path("/mnt/data/Murphy/src")
    """La RACINE du corpus — un chemin **absolu**, hors du dépôt.

    Le sous-répertoire de chaque source (`LEGI`, `CASS`…) est un fait sur la source, pas
    de la config : il vit dans `sources/registry.py`.

    Le défaut était `data/01_raw`, un chemin **relatif au CWD qui ne pointait sur rien** —
    et son mode de défaillance est muet : un répertoire absent ne lève pas, il donne zéro
    document. Un corpus vide et un run « réussi » sont indiscernables. Absolu, donc, parce
    que le corpus ne vit dans aucun des deux dépôts."""

    source: str = "all"
    """Les sources ingérées par défaut. **`all` = toutes les sources ingérables.**

    Surchargeable : `kedro run --params source=cass`, ou `source=cass,jade` pour un
    sous-ensemble.

    **Pourquoi « toutes » est le bon défaut.** Le défaut d'un pipeline d'ingestion doit
    être *ingérer le corpus*, pas *ingérer un sixième du corpus*. `legi` en défaut était
    un vestige de l'époque où LEGI était la seule source écrite : il faisait qu'un
    `kedro run` nu laissait cinq bases sur six intactes — sans le dire, et en se
    terminant « ok ». Un run qui n'ingère pas ce qu'on croit qu'il ingère est exactement
    la famille d'échec silencieux que ce pipeline s'interdit.

    Toutes les sources partagent la même collection Qdrant : même normalisation, même
    chunking, même modèle."""
    meta_jsonl_dir: Path = Path("data/08_reporting")

    @field_validator("qdrant_api_key", mode="after")
    @classmethod
    def _secret_vide_vaut_absent(cls, value: SecretStr | None) -> SecretStr | None:
        """``QDRANT_API_KEY=`` produit ``SecretStr('')``, **pas** ``None``.

        Même piège que ``EMBEDDING_API_KEY``, une couche plus bas : le type optionnel dit
        « une clé, ou aucune », et la chaîne vide n'est ni l'un ni l'autre. Le client
        Qdrant recevrait une clé d'API *vide* au lieu de n'en recevoir aucune — un refus
        d'authentification là où on voulait ne pas s'authentifier du tout.
        """
        if value is not None and not value.get_secret_value():
            return None
        return value


class EmbeddingRuntimeSettings(BaseSettings):
    """Comment on **atteint** le modèle — pas quel modèle, ni quelle dimension.

    Le modèle et sa dimension sont dans ``parameters.yml`` (bloc ``embedding``). Ce qui
    reste ici est le transport : un fournisseur, une clé d'API, une URL de service, une
    taille de lot.

    ⚠️ ``provider="noop"`` produit des vecteurs nuls et les écrit dans la collection du
    *vrai* modèle. C'est une hygiène de test, qui n'est garantie par rien.
    """

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE, env_prefix="embedding_", extra="ignore"
    )

    provider: Literal["local", "noop", "openai"] = "noop"
    batch_size: int = 32

    api_key: str | None = None
    service_url: str | None = None

    @field_validator("api_key", "service_url", mode="after")
    @classmethod
    def _vide_vaut_absent(cls, value: str | None) -> str | None:
        """``EMBEDDING_API_KEY=`` dans un ``.env`` produit ``''``, **pas** ``None``.

        La chaîne vide n'est pas une valeur, c'est l'absence — et les deux champs sont lus
        comme telle : ``OpenAIEmbedder`` ne pose l'en-tête ``Authorization`` que si la clé
        est *vraie*, et une ``service_url`` vide doit être refusée comme une absente, pas
        interprétée comme une URL. Laisser passer ``''`` fait dépendre la correction de la
        *falsyness* de chaque appelant : le jour où l'un écrit ``is not None``, il envoie
        un ``Bearer`` vide et récolte un 401 que rien n'explique.
        """
        return value or None


@lru_cache
def get_infra_settings() -> InfraSettings:
    _require_env_file()
    return InfraSettings()


@lru_cache
def get_embedding_runtime_settings() -> EmbeddingRuntimeSettings:
    _require_env_file()
    return EmbeddingRuntimeSettings()
