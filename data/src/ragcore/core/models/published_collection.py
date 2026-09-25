"""Le POINTEUR de collection — ce que le serving doit lire, et rien d'autre.

Le nom d'une collection Qdrant est une **empreinte** (§6) : `9424808d…`, dérivée de la
config de workflow. C'est ce qui permet à deux configs de coexister — la condition de
l'A/B. Mais ça pose au serving une question qu'il ne peut pas résoudre seul :
**laquelle fait foi ?**

Le backend lisait `QDRANT_COLLECTION=chunks`, un nom écrit à la main **qui n'existe
pas**. Et l'A/B sur `chunk_size` a laissé quatre collections empreintées côte à côte :
il n'y avait plus une candidate mais quatre, et rien pour trancher.

D'où ce document, écrit par le pipeline et lu par le backend au boot. Il ne dit pas
« voici les collections qui existent » — il dit **« voici celle qui fait foi »**.

**Seul un run `ok` le met à jour.** Un run `degraded` a laissé un corpus incomplet ;
publier son empreinte propagerait la fuite jusqu'à l'utilisateur, qui n'aurait aucun
moyen de le savoir. C'est le point où l'équation de complétude cesse d'être un outil de
diagnostic pour devenir **la condition de publication** — et c'est aussi pourquoi la
non-fuite télémétrique était un prérequis : ce statut ne vaut que ce que valent ses
compteurs.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from .identifiers import RunId

__all__ = [
    "PublishedCollection",
    "POINTER_KEY",
    "SERVING_CONTRACT_VERSION",
    "may_publish",
]

SERVING_CONTRACT_VERSION = 1
"""La version du contrat ingestion ↔ serving que ce code écrit (ADR-039).

La v1 couvre :

- le payload Qdrant : ``chunk_id``, ``identifier``, ``owner_id``, ``char_start``,
  ``char_end`` (points de code dans ``content``), ``type_document`` facultatif ;
- Mongo ``documents`` : ``identifier``, ``owner_id``, ``title``, ``content`` ;
- ce pointeur, qui publie la version.

Le backend refuse de démarrer sur une autre version. Toute modification de ces champs
est donc un **bump**, et un bump impose un run complet (voir ``may_publish``).
"""

POINTER_KEY = "current"
"""La clé du pointeur — il n'y en a QU'UN.

Un singleton, pas une collection de pointeurs : « quelle collection fait foi ? » n'a
qu'une réponse. La clé fixe donne l'idempotence de l'`upsert` sans inventer d'identité.
"""


class PublishedCollection(BaseModel):
    """La collection Qdrant qui FAIT FOI, et la trace de qui l'a publiée."""

    model_config = ConfigDict(frozen=True)

    key: str = POINTER_KEY

    collection_name: str
    """L'empreinte (`9424808d…`). C'est ce que le backend interroge."""

    fingerprint: str
    """Identique à ``collection_name`` aujourd'hui (§6) — mais nommé à part.

    Les deux se confondent *par décision*, pas par nature : le jour où le nom gagne un
    préfixe ou un suffixe, le serving doit continuer de lire un NOM, et la traçabilité
    doit continuer de lire une EMPREINTE. Les fusionner ici obligerait à les démêler
    plus tard, sur un champ déjà en base.
    """

    run_id: RunId
    """Le run qui a publié. Sans lui, « d'où sort ce corpus ? » n'a pas de réponse."""

    document_count: int
    """Combien de documents ce corpus contient. Le serving n'en a pas besoin ; l'humain
    qui débogue un « pourquoi ne trouve-t-il rien ? », si."""

    published_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    serving_contract_version: int | None = None
    """La version du contrat que cette collection respecte (``SERVING_CONTRACT_VERSION``).

    ``None`` par défaut, et non la version courante : un pointeur écrit avant l'ADR-039
    doit se relire « sans version », pas se faire passer pour la v1. ``of`` la pose.
    """

    @classmethod
    def of(
        cls,
        collection_name: str,
        *,
        run_id: RunId,
        document_count: int,
    ) -> "PublishedCollection":
        return cls(
            collection_name=collection_name,
            fingerprint=collection_name,
            run_id=run_id,
            document_count=document_count,
            serving_contract_version=SERVING_CONTRACT_VERSION,
        )


def may_publish(current: PublishedCollection | None, *, is_full_run: bool) -> bool:
    """Un run ``ok`` peut-il publier sans mêler deux versions du contrat ?

    Un run complet réécrit tous les documents : il publie toujours. Un run restreint
    (``--params source=…``) ne réécrit que ses sources ; s'il publiait une version que
    le pointeur en place ne porte pas encore, la collection mêlerait deux formats sous
    une version qui prétend le contraire. Il ne publie donc que si le pointeur porte
    déjà la version de ce code.
    """
    if is_full_run:
        return True
    return (
        current is not None
        and current.serving_contract_version == SERVING_CONTRACT_VERSION
    )
