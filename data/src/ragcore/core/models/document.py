from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from .citation import Citation
from .enums import SourceName
from .identifiers import OwnerId, SourceIdentifier

SCHEMA_VERSION = 3
"""v3 (18 juil. 2026) : ``citations`` ajouté — les cibles décrites (``<LIEN>`` à ``@id``
vide) deviennent un champ du document au lieu de nœuds ``:Unknown`` dans le graphe.

v2 (ADR-022, B-00) : ``unknowns`` et ``parsed_at`` retirés, ``source_files`` ajouté,
clés de métadonnées au CHEMIN COMPLET. Un bump = une ré-ingestion complète, groupée."""


class RawDocument(BaseModel):
    """Document tel que récupéré par le connector, avant parsing."""

    model_config = ConfigDict(frozen=True)

    source: SourceName
    source_document_id: str
    payload: dict[str, Any]
    fetched_at: datetime
    owner_id: OwnerId


class ParsedDocument(BaseModel):
    """Document après parsing : structuré, prêt pour le chunking.

    Un seul ``identifier`` (union discriminée ``SourceIdentifier``) nomme le document,
    quelle que soit sa source : c'est lui, et lui seul, qui sert de clé partout en aval
    (Mongo, Qdrant, nœud Neo4j). Pas de hash de contenu : l'idempotence se joue sur la
    présence de l'identifiant, pas sur une comparaison d'octets.

    **Plus de champ ``unknowns``** (ADR-022 §1, modèle « trois portes ») : une balise
    non-configurée n'est pas un aveu qui voyage dans la donnée — c'est une MÉTADONNÉE
    (clé chemin-complet), ou un LIEN si sa valeur référence un document. Le signal
    ``tag.unconfigured``, lui, part en télémétrie au site de parse, jamais en base.

    **Plus de ``parsed_at``** : doublon du ``processed_at`` du manifest — deux
    horodatages pour un même fait finissent par diverger.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: int = SCHEMA_VERSION
    identifier: SourceIdentifier
    source: SourceName
    owner_id: OwnerId

    title: str
    content: str
    structure: dict[str, Any]
    metadata: dict[str, Any]

    citations: tuple[Citation, ...] = ()
    """Les cibles que le document DÉSIGNE sans les identifier (``<LIEN>`` à ``@id`` vide).

    Elles ne sont pas des arêtes : « code de l'environnement » ou « Articles 706-95-16 et
    suivants du code de procédure pénale » sont des *phrases*, et aucun run futur ne les
    fera exister comme documents. Les matérialiser en nœuds ``:Unknown`` — ce que faisait
    la version précédente — peuplait le graphe d'entités jamais résolues, une par
    formulation. Une citation est une propriété de celui qui l'énonce ; elle vit ici.

    Rempli APRÈS le parse, par le worker : l'extraction des liens est ce qui distingue une
    cible identifiée d'une cible décrite, et elle tourne un cran plus tard.
    """

    source_files: tuple[str, ...] = ()
    """Les FICHIERS XML dont ce document est issu (un article LEGI = jusqu'à 2 facettes).

    De la provenance, pas du contenu : ce champ sert l'inspection Neo4j en dev
    (``include_path``, ADR-022 amendé) et n'est JAMAIS persisté dans Mongo — le dépôt
    l'exclut du dump. Un chemin absolu du poste d'ingestion n'a de sens nulle part
    ailleurs que sur ce poste.
    """
