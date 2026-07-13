"""``WorkflowConfig`` — la référence d'un run, et ce qu'on hashe.

**C'est cet objet la vérité, pas ``parameters.yml``** (§9). Kedro ne fait que
l'instancier depuis le YAML et l'injecter ; le YAML est *une façon de le peupler*,
pas la spécification. Un run lancé depuis un CLI ou un test construit le même objet
sans qu'aucun YAML n'existe.

**Ce qui entre ici, et le critère qui le décide.** Une seule question : *est-ce qu'en
changer la valeur invalide les vecteurs déjà produits ?* Si oui, c'est du workflow —
les anciens et les nouveaux vecteurs ne sont plus comparables, ils ne peuvent pas
cohabiter dans une collection. Si non, c'est de l'infra (``adapters/config/``).

    chunk_size: 128 → 256      ⇒ les vecteurs changent   ⇒ ICI
    MONGODB_URI: localhost → docker  ⇒ les vecteurs sont identiques  ⇒ PAS ici

Trois étapes passent le critère, et elles seules (§6) : la **normalisation** (§4), le
**chunking** (§5) et l'**embedding**. Le reste — URIs, secrets, chemins, ``run_id``,
``owner_id``, nombre de workers — est opérationnel : il dit *où* et *comment*, jamais
*quoi*.

**Pourquoi c'est structurel et pas cosmétique.** §6 nomme la collection Qdrant par le
hash de cette config. Si le hash mangeait toute la configuration, il mangerait l'URI
Mongo : passer de ``localhost`` au conteneur Docker créerait une collection neuve
alors qu'on produit rigoureusement les mêmes vecteurs. L'A/B serait perdu pour une
raison qui n'a aucun sens. D'où la scission — et le fait que ``fingerprint()`` n'a
*physiquement* pas accès à l'infra : l'erreur devient impossible par construction, au
lieu d'être évitée par la discipline de qui pense à exclure les bons champs.

Les modèles sont **gelés** (``frozen=True``) : une config qu'on hashe ne doit pas
pouvoir changer entre le moment où on la hashe et celui où on l'utilise.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ChunkingConfig",
    "EmbeddingConfig",
    "NormalizationConfig",
    "WorkflowConfig",
]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class NormalizationConfig(_Frozen):
    """§4 — la normalisation typographique.

    ``version`` est la seule chose qui entre dans le hash, et c'est **suffisant** : la
    fonction de normalisation est pure, donc sa version identifie entièrement son
    comportement. Elle invalide tous les embeddings si elle bouge — d'où la règle : on
    ne modifie jamais la normalisation sans incrémenter la version, et l'incrémenter
    crée mécaniquement une collection neuve.

    À ce jour la normalisation typographique de §4 (NFC, insécables, guillemets,
    tirets) **n'est pas écrite** — d'où ``"none"``. Le jour où elle atterrit, elle
    exporte sa propre constante de version et ce champ la lit : le changement de
    collection sera alors automatique, et non un geste à ne pas oublier.
    """

    version: str = Field(default="none", min_length=1)


class ChunkingConfig(_Frozen):
    """§5 — la découpe.

    ``strategy`` nomme la *méthode* (où l'on coupe), ``size``/``overlap`` la règlent.
    Les trois entrent dans le hash parce que §5 veut pouvoir **comparer des méthodes
    de chunking** : chaque méthode a donc sa collection, et l'A/B se lit dans MLflow.
    """

    strategy: str = Field(min_length=1)
    size: int = Field(gt=0)
    overlap: int = Field(ge=0)


class EmbeddingConfig(_Frozen):
    """§6 — le modèle et sa dimension.

    ``provider`` (local / openai / noop) n'est **pas** ici, et c'est délibéré : deux
    façons d'atteindre le *même* modèle produisent les mêmes vecteurs. Hasher le
    provider fragmenterait les collections en passant d'un embedder local à un service
    TEI — exactement le faux positif que la scission cherche à éviter. Le provider est
    donc de l'infra.
    """

    model_name: str = Field(min_length=1)
    dimension: int = Field(gt=0)


class WorkflowConfig(_Frozen):
    """L'objet qu'on hashe. Il ne connaît aucune URI, et il ne peut pas en connaître.

    Ajouter ici un champ d'infrastructure (une URI, un secret, un chemin) casserait
    l'A/B en silence. Le cliquet ``golden/test_fingerprint.py`` refuse le build si ça
    arrive : la garantie est exécutable, pas déclarative.
    """

    normalization: NormalizationConfig
    chunking: ChunkingConfig
    embedding: EmbeddingConfig
