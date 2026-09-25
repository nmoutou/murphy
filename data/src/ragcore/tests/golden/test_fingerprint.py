"""CLIQUET — l'empreinte de config (§6).

Un test unitaire échoue quand on casse le code. **Un golden échoue quand on change la
doctrine sans s'en rendre compte** — et c'est exactement le risque ici.

Le nom de la collection Qdrant EST cette empreinte. Si la canonicalisation bouge, tous
les noms de collection bougent : les vecteurs déjà écrits deviennent orphelins, le
prochain run les réécrit ailleurs, et **rien ne le signale**. Les hashs littéraux
ci-dessous rendent ce changement visible en revue. Les mettre à jour pour faire passer
le build est un geste — c'est précisément l'effet recherché.

Le dernier test est d'une autre nature : il ne vérifie pas une valeur, il vérifie qu'une
**erreur reste impossible**.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from kedro.config import OmegaConfigLoader

from ragcore.adapters.config.settings import InfraSettings
from ragcore.core.config import (
    ChunkingConfig,
    EmbeddingConfig,
    NormalizationConfig,
    WorkflowConfig,
    canonicalize,
    collection_name,
    fingerprint,
)
from ragcore.orchestration.kedro.hooks import _build_workflow_config
from ragcore.sources.generic import NORMALIZATION_VERSION

_CONF_SOURCE = Path(__file__).parents[3].parent / "conf"
"""Le VRAI répertoire de config de production (partition ADR-026 : `base/workflow/`,
`base/ingestion/`, `base/evaluation/`). Le charger via le VRAI loader Kedro — et non un
``yaml.safe_load`` — est tout l'objet des deux derniers cliquets : c'est la fusion
multi-fichiers réelle qui doit reproduire l'empreinte figée, pas une lecture ad hoc."""


def _params_reels() -> dict:
    """Charge `parameters` depuis `conf/` exactement comme Kedro le fait au runtime."""
    loader = OmegaConfigLoader(
        conf_source=str(_CONF_SOURCE), base_env="base", default_run_env="base"
    )
    return loader["parameters"]


# La config du corpus LEGI telle que `parameters.yml` la peuple aujourd'hui. Elle sert
# de référence : c'est SON empreinte qui nomme la collection en production.
#
# `test_le_yaml_reel_produit_bien_cette_empreinte` VÉRIFIE cette affirmation, au lieu de
# la commenter. Sans lui, cette constante pourrait dériver du vrai `parameters.yml` sans
# que rien ne l'attrape — et le cliquet figerait alors l'empreinte d'une config que
# personne ne fait tourner.
_LEGI = WorkflowConfig(
    normalization=NormalizationConfig(version="v1"),
    chunking=ChunkingConfig(strategy="legi-structural-v1", size=384, overlap=25),
    embedding=EmbeddingConfig(
        model_name="sentence-transformers/all-mpnet-base-v2", dimension=768
    ),
)

# ⚠️ FIGÉ. Changer cette valeur, c'est renommer la collection de production.
#
# Elle a bougé DEUX fois, sciemment :
#
#   `1ef32cd5…` → `3119c73a…`  la normalisation typographique (§4) passe de `none` à `v1`.
#   `3119c73a…` → `9424808d…`  `chunk_size` passe de 128 à 384 caractères.
#
# Le second changement est un arbitrage MESURÉ, pas un réglage : à 128, un run coûtait
# 838 s pour 61 975 chunks (l'embedding est 99,9 % du temps). À 384 il coûte 173 s pour
# 18 090 chunks — et **zéro document perdu**, vérifié au tokenizer du modèle sur les six
# sources (300 tokens au maximum, sous la fenêtre de 384). Au-delà, on perd des documents :
# 512 en a perdu 1, 1024 en a perdu 98.
_LEGI_FINGERPRINT = "9424808d1c636d533648bbf4e77f2496"

_LEGI_FINGERPRINT_CHUNK_128 = "3119c73ab26b71121e40e079abe5a06c"
"""L'empreinte d'avant le passage à `chunk_size: 384`. Ses vecteurs existent toujours,
dans leur propre collection — c'est très exactement ce que §6 promet : changer un
paramètre de traitement ne PIÉTINE pas les vecteurs d'avant, il en crée d'autres à côté."""

_LEGI_FINGERPRINT_AVANT_NORMALISATION = "1ef32cd5c8a3f731b657e0d5aa3a4c03"
"""L'empreinte d'AVANT §4. Gardée pour une raison : c'est le nom de la collection où
vivent les vecteurs déjà écrits. La connaître, c'est pouvoir les retrouver — et prouver
qu'ils n'ont pas été écrasés."""


def test_l_empreinte_de_la_config_LEGI_est_figee() -> None:
    """L'engagement de §6 : même config → même hash, **pour toujours**."""
    assert fingerprint(_LEGI) == _LEGI_FINGERPRINT


def test_la_collection_EST_l_empreinte_sans_prefixe() -> None:
    """Pas de segment lisible : un nom « parlant » redeviendrait le nom fragile que le
    hash remplace. L'opacité est assumée — le run MLflow porte les params en clair.
    """
    assert collection_name(_LEGI) == _LEGI_FINGERPRINT


def test_la_forme_canonique_est_figee() -> None:
    """C'est ici que se joue la stabilité : le hash n'est qu'une compression de ceci.

    Figer la forme canonique **en plus** du hash rend le diagnostic lisible le jour où
    le cliquet casse : on voit *ce qui* a changé, pas seulement *que* ça a changé.
    """
    assert canonicalize(_LEGI) == (
        '{"chunking":{"overlap":25,"size":384,"strategy":"legi-structural-v1"},'
        '"embedding":{"dimension":768,"model_name":"sentence-transformers/all-mpnet-base-v2"},'
        '"normalization":{"version":"v1"}}'
    )


@pytest.mark.parametrize(
    ("champ", "config"),
    [
        (
            "chunk_size",
            _LEGI.model_copy(
                update={"chunking": _LEGI.chunking.model_copy(update={"size": 256})}
            ),
        ),
        (
            "chunk_overlap",
            _LEGI.model_copy(
                update={"chunking": _LEGI.chunking.model_copy(update={"overlap": 50})}
            ),
        ),
        (
            "strategy",
            _LEGI.model_copy(
                update={
                    "chunking": _LEGI.chunking.model_copy(update={"strategy": "flat"})
                }
            ),
        ),
        (
            "modele",
            _LEGI.model_copy(
                update={
                    "embedding": _LEGI.embedding.model_copy(
                        update={"model_name": "camembert"}
                    )
                }
            ),
        ),
        (
            "dimension",
            _LEGI.model_copy(
                update={
                    "embedding": _LEGI.embedding.model_copy(update={"dimension": 1024})
                }
            ),
        ),
        (
            # `v1` est la version EN COURS : la variante doit donc être la SUIVANTE.
            # C'est la vraie question posée à ce cliquet — le jour où la normalisation
            # évolue encore, produira-t-elle bien une collection neuve ?
            "norm_version",
            _LEGI.model_copy(
                update={
                    "normalization": _LEGI.normalization.model_copy(
                        update={"version": "v2"}
                    )
                }
            ),
        ),
        (
            # Le retour en arrière compte aussi : revenir à `none` doit ramener
            # EXACTEMENT l'empreinte d'avant §4, sans quoi les vecteurs déjà écrits
            # seraient devenus introuvables.
            "norm_version_retour",
            _LEGI.model_copy(
                update={
                    "normalization": _LEGI.normalization.model_copy(
                        update={"version": "none"}
                    )
                }
            ),
        ),
    ],
)
def test_tout_champ_semantique_change_l_empreinte(
    champ: str, config: WorkflowConfig
) -> None:
    """Chacun de ces champs invalide les vecteurs déjà produits. Chacun doit donc créer
    une collection neuve — sans quoi deux stratégies s'écraseraient en silence dans la
    même collection, et l'A/B de §6 mesurerait un mélange.

    ``norm_version`` compte au même titre que les autres, et **ce n'est plus une
    hypothèse** : le passage de §4 de ``none`` à ``v1`` a bel et bien déplacé la
    collection (``1ef32cd5…`` → ``3119c73a…``). Ce champ a fait son travail tout seul,
    sans qu'on ait eu à y penser — c'était l'objet du dispositif.
    """
    assert fingerprint(config) != _LEGI_FINGERPRINT, (
        f"{champ} n'a pas bougé l'empreinte"
    )


def test_l_empreinte_ne_depend_pas_de_l_ordre_de_construction() -> None:
    """La canonicalisation trie : l'ordre des champs ne doit jamais changer le hash."""
    autre = WorkflowConfig(
        embedding=EmbeddingConfig(
            dimension=768, model_name="sentence-transformers/all-mpnet-base-v2"
        ),
        chunking=ChunkingConfig(overlap=25, strategy="legi-structural-v1", size=384),
        normalization=NormalizationConfig(version="v1"),
    )
    assert fingerprint(autre) == _LEGI_FINGERPRINT


def test_l_infra_ne_peut_PHYSIQUEMENT_pas_entrer_dans_l_empreinte() -> None:
    """LE cliquet structurel — il ne vérifie pas une valeur, mais une **impossibilité**.

    §6 : « ``fingerprint()`` n'a physiquement pas accès à l'URI Mongo : l'erreur est
    impossible par construction, pas évitée par convention. » Ce test exécute cette
    phrase.

    Le danger qu'il garde : quelqu'un ajoute un champ d'infra au ``WorkflowConfig`` —
    par commodité, pour « tout avoir au même endroit ». Le hash mangerait alors l'URI
    Mongo, et passer de ``localhost`` au conteneur Docker créerait une collection neuve
    alors qu'on produit **rigoureusement les mêmes vecteurs**. L'A/B serait perdu pour
    une raison qui n'a aucun sens, et personne ne s'en apercevrait.

    On ne se contente donc pas d'une liste noire de noms devinés : on prend les champs
    **réels** de l'``InfraSettings`` et on exige que le ``WorkflowConfig`` n'en porte
    aucun. La frontière est vérifiée contre les deux moitiés, pas contre un souvenir.
    """
    infra = set(InfraSettings.model_fields)
    workflow = _champs_recursifs(WorkflowConfig)

    intrus = workflow & infra
    assert not intrus, (
        f"Champs d'infrastructure trouvés dans WorkflowConfig : {sorted(intrus)}. "
        "Ils seraient hashés — un déménagement de base renommerait la collection."
    )
    # Et la garantie de fond : la fonction ne prend rien d'autre qu'un WorkflowConfig.
    with pytest.raises(AttributeError):
        fingerprint("mongodb://localhost:27017")  # type: ignore[arg-type]


def test_les_vecteurs_ecrits_AVANT_la_normalisation_restent_retrouvables() -> None:
    """L'A/B n'a de sens que si l'ancienne collection existe encore — et se retrouve.

    Passer la normalisation de ``none`` à ``v1`` a créé une collection neuve. Les vecteurs
    d'avant vivent donc toujours dans ``1ef32cd5…`` : ils n'ont **pas** été écrasés, c'est
    tout l'objet du hash. Encore faut-il savoir les nommer pour aller les chercher.

    Ce test prouve que la fonction est **réversible sur sa clé** : reposer la config
    d'avant redonne le nom d'avant, au caractère près. Sans cette propriété, chaque
    changement de normalisation abandonnerait un jeu de vecteurs anonyme dans Qdrant —
    payé, calculé, et introuvable.

    La config historique est écrite **en entier**, pas dérivée de ``_LEGI`` : elle est un
    fait du passé, elle ne doit pas bouger quand la config courante bouge. La dériver
    l'avait justement cassée au passage de ``chunk_size`` à 384.
    """
    avant = WorkflowConfig(
        normalization=NormalizationConfig(version="none"),
        chunking=ChunkingConfig(strategy="legi-structural-v1", size=128, overlap=25),
        embedding=EmbeddingConfig(
            model_name="sentence-transformers/all-mpnet-base-v2", dimension=768
        ),
    )
    assert collection_name(avant) == _LEGI_FINGERPRINT_AVANT_NORMALISATION


def test_les_vecteurs_de_chunk_128_restent_retrouvables() -> None:
    """Même propriété, pour le passage de ``chunk_size`` 128 → 384.

    Les 61 975 vecteurs calculés à 128 vivent toujours dans ``3119c73a…``. Ce test dit
    qu'on sait encore les nommer — donc les comparer, donc y revenir.
    """
    avant = WorkflowConfig(
        normalization=NormalizationConfig(version="v1"),
        chunking=ChunkingConfig(strategy="legi-structural-v1", size=128, overlap=25),
        embedding=EmbeddingConfig(
            model_name="sentence-transformers/all-mpnet-base-v2", dimension=768
        ),
    )
    assert collection_name(avant) == _LEGI_FINGERPRINT_CHUNK_128


def test_le_yaml_REEL_produit_bien_l_empreinte_figee() -> None:
    """Le cliquet qui rattache le golden au MONDE. Sans lui, il fige une fiction.

    Les tests ci-dessus figent l'empreinte d'un ``WorkflowConfig`` construit **à la main**.
    C'est le bon choix — un golden ne doit pas dépendre d'un fichier qui bouge. Mais il
    ouvre alors un trou : ``parameters.yml`` pourrait dériver de cette constante sans que
    rien ne l'attrape, et le cliquet garderait fidèlement l'empreinte d'une config que
    **personne ne fait tourner**.

    Ce test charge la VRAIE config via le VRAI loader Kedro (fusion multi-fichiers de la
    partition `workflow/ingestion/evaluation` — ADR-026), la passe par la vraie fonction
    du hook, et exige la même empreinte. Il est la couture entre ce qui est figé et ce qui
    est exécuté — et, depuis B-14, la preuve que la restructuration de `conf/` n'a pas
    déplacé la collection.
    """
    params = _params_reels()
    depuis_le_yaml = _build_workflow_config(params)

    assert depuis_le_yaml == _LEGI, (
        "parameters.yml a divergé de la config figée par ce cliquet. "
        "L'un des deux ment — et c'est le YAML qui tourne en production."
    )
    assert collection_name(depuis_le_yaml) == _LEGI_FINGERPRINT


def test_la_version_de_normalisation_du_CODE_est_celle_du_YAML() -> None:
    """La couture entre le traitement et le hash qui le nomme.

    ``NORMALIZATION_VERSION`` vit dans le code (``sources/generic/normalize.py``), et le
    hash lit ``parameters.yml``. **Rien ne les relie**, sauf ce test.

    Le danger, s'ils divergent : on améliore la normalisation, le texte embarqué change,
    les vecteurs changent — mais la version du YAML n'a pas bougé, donc le hash n'a pas
    bougé, donc **les nouveaux vecteurs sont écrits dans la collection des anciens**. Deux
    jeux incomparables dans un même index, et pas une ligne de log. C'est exactement le
    trou que §6 prétend fermer ; sans ce test, il reste ouvert par le bas.
    """
    params = _params_reels()
    du_yaml = params["workflow"]["normalization"]["version"]

    assert du_yaml == NORMALIZATION_VERSION, (
        f"Le code normalise en '{NORMALIZATION_VERSION}' mais le YAML déclare "
        f"'{du_yaml}'. Le hash ne verrait donc PAS le changement de traitement, et les "
        "nouveaux vecteurs iraient écraser les anciens dans la même collection."
    )


def _champs_recursifs(model: type) -> set[str]:
    """Les noms de champs d'un modèle pydantic, imbriqués compris."""
    noms: set[str] = set()
    for nom, champ in model.model_fields.items():  # type: ignore[attr-defined]
        annotation = champ.annotation
        if annotation is not None and hasattr(annotation, "model_fields"):
            noms |= _champs_recursifs(annotation)
        else:
            noms.add(nom)
    return noms
