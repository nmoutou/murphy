from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from .citation import Citation
from .enums import SourceName
from .identifiers import Identifier


class RawDocument(BaseModel):
    """Document tel que récupéré par le connector, avant parsing."""

    model_config = ConfigDict(frozen=True)

    source: SourceName
    source_document_id: str
    payload: dict[str, Any]
    fetched_at: datetime


class ParsedDocument(BaseModel):
    """Document après parsing : structuré, prêt pour le chunking.

    Un seul ``identifier`` nomme le document, quelle que soit sa source : c'est lui, et lui seul, qui sert de clé partout en aval
    (Mongo, Qdrant, nœud Neo4j). Pas de hash de contenu : chaque run réécrit le document
    en place sous cet identifiant, sans comparer d'octets.

    **Plus de champ ``unknowns``** (ADR-022 §1, modèle « trois portes ») : une balise
    non-configurée n'est pas un aveu qui voyage dans la donnée — c'est une MÉTADONNÉE
    (clé chemin-complet), ou un LIEN si sa valeur référence un document. Le signal
    ``tag.unconfigured``, lui, part en télémétrie au site de parse, jamais en base.

    **Plus de ``parsed_at``** : doublon de l'horodatage de ``document.persisted`` dans
    l'audit — deux horodatages pour un même fait finissent par diverger.
    """

    model_config = ConfigDict(frozen=True)

    identifier: Identifier
    source: SourceName

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

    De la provenance, pas du contenu : ce champ sert l'inspection en dev, et n'est écrit
    dans Mongo et sur le nœud Neo4j qu'avec ``include_path`` (``parameters.yml``,
    ADR-022 amendé) — sinon les dépôts l'excluent. Un chemin absolu du poste
    d'ingestion n'a de sens nulle part ailleurs que sur ce poste.
    """
