"""Embedder distant — API compatible OpenAI (le service TEI du docker-compose).

Par lots : un corpus de dix mille chunks en dix mille requêtes HTTP serait lent
sans raison, et ferait tomber le service bien avant d'être lent.
"""

import asyncio
import logging
import threading
from urllib.parse import urlsplit, urlunsplit

import httpx

from ragcore.core.exceptions import EmbeddingModelMismatchError
from ragcore.core.models.chunk import Chunk, EmbeddedChunk

__all__ = ["OpenAIEmbedder", "assert_service_serves_model"]

_LOGGER = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 120.0
_INFO_TIMEOUT_SECONDS = 10.0

# Le service refuse un lot qui dépasse la fenêtre du modèle. Ce n'est PAS une panne : c'est
# lui qui nous apprend la limite, et c'est la seule façon fiable de la connaître — le
# chunker compte en caractères, le modèle en tokens, et le ratio varie d'un facteur 10
# selon le texte (mesuré : 3,08 car/token en moyenne, 0,33 au pire).
_PAYLOAD_TOO_LARGE = 413


def _rejected(chunk: Chunk) -> ValueError:
    return ValueError(
        f"Le service refuse le chunk {chunk.chunk_id} même vide : le rejet n'est pas une "
        f"question de taille. Vérifier la santé du service d'embedding."
    )


async def assert_service_serves_model(base_url: str, expected_model: str) -> None:
    """Le service sert-il bien le modèle dont le nom **baptise la collection** (§6) ?

    TEI ignore le champ ``model`` de la requête : il ne sert que le modèle de son
    ``--model-id``. Une divergence entre le conteneur et ``parameters.yml`` écrit donc les
    vecteurs d'un modèle dans la collection nommée d'après un autre, **sans rien lever**.
    ``GET /info`` est le seul endroit où le service *dit* ce qu'il sert : c'est la seule
    façon de fermer le trou.

    Appelée **avant le pool** (depuis le hook), jamais depuis un worker — voir
    ``EmbeddingModelMismatchError``. Un service injoignable est **fatal** lui aussi : tant
    qu'on ne peut pas vérifier ce qu'il sert, on n'écrit pas.

    Miroir exact du garde-fou de dimension de ``_embed_batch`` : même esprit, même moment
    (avant d'écrire), même verdict (on refuse d'écrire).
    """
    # `/info` est à la RACINE du service, pas sous le préfixe `/v1` de l'API compatible
    # OpenAI. Interroger `{base_url}/info` donnerait un 404 — donc un garde-fou qui ne se
    # déclencherait jamais, ce qui est pire que pas de garde-fou du tout.
    parts = urlsplit(base_url)
    info_url = urlunsplit((parts.scheme, parts.netloc, "/info", "", ""))

    try:
        async with httpx.AsyncClient(timeout=_INFO_TIMEOUT_SECONDS) as client:
            response = await client.get(info_url)
            response.raise_for_status()
            served = response.json().get("model_id")
    except (httpx.HTTPError, ValueError) as exc:
        raise EmbeddingModelMismatchError(
            f"Impossible d'interroger {info_url} : {exc}. Le service d'embedding "
            f"est-il démarré (`npm run up`) ? Tant qu'on ne peut pas VÉRIFIER quel "
            f"modèle il sert, on n'écrit pas."
        ) from exc

    if served != expected_model:
        raise EmbeddingModelMismatchError(
            f"Le service sert « {served} », or la configuration déclare "
            f"« {expected_model} ». TEI ignore le champ `model` de la requête : il ne "
            f"sert QUE le modèle de son `--model-id`. Continuer écrirait les vecteurs de "
            f"« {served} » dans la collection nommée d'après l'empreinte de "
            f"« {expected_model} », sans que rien ne le signale. Aligner EMBEDDING_MODEL "
            f"(.env.dev, à la racine) et embedding.embedding.embedding_model "
            f"(conf/base/parameters.yml)."
        )


class OpenAIEmbedder:
    """Implémentation de ``BaseEmbedder`` via ``POST /embeddings``."""

    def __init__(
        self,
        model_name: str,
        dimension: int,
        api_key: str | None = None,
        batch_size: int = 32,
        base_url: str | None = None,
    ) -> None:
        if not base_url:
            # L'ancien défaut retombait sur `https://api.openai.com/v1` : un
            # EMBEDDING_SERVICE_URL oublié envoyait SILENCIEUSEMENT tout le corpus chez
            # OpenAI — facturé, et avec un autre modèle que celui dont le nom baptise la
            # collection. Un défaut ne doit jamais désigner un service tiers payant.
            raise ValueError(
                "OpenAIEmbedder exige une `base_url` explicite. Renseigner "
                "EMBEDDING_SERVICE_URL (p. ex. http://localhost:5001/v1)."
            )
        self._model_name = model_name
        self._dimension = dimension
        self._api_key = api_key
        self._batch_size = batch_size
        self._base_url = base_url.rstrip("/")
        # Quels CHUNKS ont dû être raccourcis pour tenir dans la fenêtre du modèle. Non
        # vide = le `chunk_size` configuré n'est PAS compatible avec le modèle, et une part
        # du corpus n'est indexée qu'en partie. Le run reste complet (aucun document
        # perdu), mais il doit le DIRE — d'où la remontée dans le bilan.
        #
        # On mémorise les `chunk_id`, pas un entier, pour deux raisons :
        #  - **compter le CHUNK, pas les moitiés.** La dichotomie raccourcit un même chunk
        #    plusieurs fois de suite (moitié, puis moitié de la moitié…) : incrémenter à
        #    chaque tour compterait 3 pour un seul chunk. Un ensemble dédoublonne — un
        #    chunk raccourci dix fois reste un chunk raccourci.
        #  - **sans course entre workers.** L'embedder est PARTAGÉ (§11) et appelé depuis
        #    plusieurs threads (un par worker, chacun sa boucle) ; `n += 1` est une
        #    lecture-modification-écriture perdable entre threads. L'écriture dans
        #    l'ensemble est protégée par un verrou : aucun raccourcissement ne s'évapore.
        self._truncated_chunk_ids: set[str] = set()
        self._truncations_lock = threading.Lock()
        # UN client par BOUCLE, pas un par appel. `embed()` est invoqué une fois par
        # document (1121 fois) : ouvrir un `AsyncClient` à chaque appel rouvrait une
        # connexion TCP vers TEI à chaque document, sans jamais réutiliser le pool.
        #
        # Pourquoi par boucle et non un attribut simple : cet embedder est PARTAGÉ entre
        # les workers (§11), et un client httpx est lié à la boucle qui l'a créé. Un
        # client unique en attribut appartiendrait à la boucle du premier worker à
        # l'appeler, et les autres échoueraient. La clé est donc la boucle courante —
        # chaque worker obtient le sien, et le réutilise sur tous ses documents.
        self._clients: dict[object, httpx.AsyncClient] = {}

    @property
    def truncations(self) -> int:
        """Combien de CHUNKS distincts ont été raccourcis — pas combien de fois.

        Lu une fois en fin de run par le hook (``_declare_truncations``), dans les deux
        chemins de sortie (succès ET erreur) : un run qui casse après avoir raccourci des
        chunks doit le dire aussi.
        """
        with self._truncations_lock:
            return len(self._truncated_chunk_ids)

    def _client(self) -> httpx.AsyncClient:
        # Pas de fermeture explicite, et c'est délibéré : chaque client appartient à la
        # boucle du worker qui l'a créé (cf. `_clients`), et un `aclose()` ne peut
        # s'exécuter que DANS cette boucle. Le hook, lui, tourne sur la boucle
        # principale — il n'a aucun moyen de fermer les clients des autres. La boucle d'un
        # worker est fermée avec le worker en fin de run ; le socket TEI part avec elle.
        # Un `aclose()` public serait donc du code qu'aucun appelant ne peut invoquer.
        loop = asyncio.get_running_loop()
        client = self._clients.get(loop)
        if client is None:
            client = httpx.AsyncClient(timeout=_TIMEOUT_SECONDS)
            self._clients[loop] = client
        return client

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        if not chunks:
            return []

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        client = self._client()
        batches = [
            chunks[start : start + self._batch_size]
            for start in range(0, len(chunks), self._batch_size)
        ]

        # Les batches d'un document partent ENSEMBLE, plus en file indienne.
        #
        # Mesuré sur ce TEI : une requête coûte ~800 ms de frais fixes, quel que soit son
        # contenu (1 texte de 2 tokens : 767 ms ; 32 textes : 1182 ms). Le temps n'est
        # donc pas dans l'inférence mais dans l'aller-retour — et TEI REGROUPE les
        # requêtes en vol côté GPU (`max_batch_tokens`). Les envoyer en série, c'est payer
        # les frais fixes une fois par batch en laissant le GPU attendre entre chacun.
        #
        # `gather` préserve l'ordre : les vecteurs restent alignés sur leurs chunks.
        results = await asyncio.gather(
            *(self._embed_batch(client, headers, batch) for batch in batches)
        )

        return [
            EmbeddedChunk(
                chunk=chunk,
                embedding=vector,
                embedding_model=self._model_name,
                embedding_dim=self._dimension,
            )
            for batch, vectors in zip(batches, results, strict=True)
            for chunk, vector in zip(batch, vectors, strict=True)
        ]

    async def _embed_batch(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        batch: list[Chunk],
    ) -> list[list[float]]:
        """Embarque un batch. Un chunk trop long est SAUVÉ, jamais perdu.

        **Le mur.** Le modèle a une fenêtre finie (mpnet : 384 tokens) et le service la
        fait respecter en REJETANT (``auto_truncate: false``) — un seul chunk trop long
        fait échouer tout le batch, donc tout le document. Mesuré : à ``chunk_size=1024``,
        **98 documents perdus** ; à 512, encore 1.

        **Pourquoi ça ne se règle pas en baissant ``chunk_size``.** Le chunker compte en
        CARACTÈRES, le modèle en TOKENS, et le ratio n'est pas constant : mesuré sur ce
        corpus, il va de 3,08 car/token en moyenne à **0,33 dans le pire cas** (chunks de
        sigles et de ponctuation, où chaque caractère est un token). Aucune valeur en
        caractères n'est sûre *par construction* — seule une garde en tokens l'est.

        **La garde.** Le 413 ne dit pas QUEL chunk déborde. On dichotomise donc : couper
        le batch en deux, réessayer. En ``log(n)`` requêtes on isole le coupable, et lui
        seul est tronqué — les autres passent intacts. Le cas nominal (aucun débordement)
        ne paie rien : une seule requête, comme avant.
        """
        response = await client.post(
            f"{self._base_url}/embeddings",
            headers=headers,
            json={"model": self._model_name, "input": [c.text for c in batch]},
        )

        if response.status_code == _PAYLOAD_TOO_LARGE:
            return await self._embed_oversized(client, headers, batch)

        response.raise_for_status()

        # L'API ne garantit pas l'ordre : elle garantit l'index. Se fier à l'ordre
        # d'arrivée associerait le vecteur d'un chunk au texte d'un autre — une
        # corruption qui ne lève rien et ne se voit qu'à la recherche.
        data = sorted(response.json()["data"], key=lambda item: item["index"])
        vectors = [item["embedding"] for item in data]

        for vector in vectors:
            if len(vector) != self._dimension:
                raise ValueError(
                    f"Le service a renvoyé des vecteurs de dimension {len(vector)}, "
                    f"or la configuration en déclare {self._dimension}. La collection "
                    f"Qdrant est créée à la dimension déclarée : les deux doivent "
                    f"coïncider."
                )
        return vectors

    async def _embed_oversized(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        batch: list[Chunk],
    ) -> list[list[float]]:
        """Un batch refusé : dichotomiser jusqu'au coupable, puis le tronquer.

        Le service ne dit pas *quel* chunk déborde — seulement que le lot déborde. Couper
        en deux et réessayer isole le fautif en ``log(n)`` requêtes, sans jamais toucher
        aux innocents.
        """
        if len(batch) > 1:
            middle = len(batch) // 2
            left, right = await asyncio.gather(
                self._embed_batch(client, headers, batch[:middle]),
                self._embed_batch(client, headers, batch[middle:]),
            )
            return [*left, *right]

        # Un seul chunk, et il ne passe pas : c'est LUI. On le raccourcit de moitié et on
        # réessaie — un vecteur calculé sur un texte amputé vaut mieux qu'un document
        # entier perdu.
        #
        # **La récursion TERMINE, par construction** : chaque tour divise la longueur par
        # deux, donc on atteint 1 caractère en `log(len)` tours au pire, et un texte d'un
        # caractère tient dans toute fenêtre concevable. C'est ce qui rend la garde sûre
        # sans avoir à connaître la fenêtre du modèle — elle la DÉCOUVRE.
        chunk = batch[0]
        if not chunk.text:
            # Rien à raccourcir : le service refuse un texte vide. Ce n'est plus une
            # question de taille — laisser remonter, l'équation de complétude le comptera.
            raise _rejected(chunk)

        shrunk = chunk.model_copy(update={"text": chunk.text[: len(chunk.text) // 2]})
        with self._truncations_lock:
            # Le `chunk_id` NE change pas quand on raccourcit le texte : les tours
            # successifs de la dichotomie ajoutent le même id, et l'ensemble ne le compte
            # qu'une fois. C'est ce qui fait qu'un chunk raccourci trois fois compte 1.
            self._truncated_chunk_ids.add(str(chunk.chunk_id))
        _LOGGER.warning(
            "chunk hors fenêtre du modèle — raccourci de %d à %d caractères (chunk_id=%s). "
            "Le document est sauvé, mais la fin de ce chunk n'est pas indexée : le vrai "
            "correctif est un `chunk_size` compatible avec la fenêtre.",
            len(chunk.text),
            len(shrunk.text),
            chunk.chunk_id,
        )
        return await self._embed_batch(client, headers, [shrunk])
