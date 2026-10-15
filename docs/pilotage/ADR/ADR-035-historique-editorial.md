# ADR-035 — L'historique éditorial : les archives DILA font foi, chaque révision est gardée

**Statut** : Proposé (15 octobre 2026) — amende ADR-034 §1 (les copies écartées deviennent
des révisions)

## Contexte

Murphy vise l'exhaustivité (ADR-005), pour un public qui n'est pas forcément juriste.
Deux historiques coexistent dans les données de la DILA, et un seul est conservé
aujourd'hui.

**L'historique juridique est déjà complet.** Dans LEGI, chaque version d'un article a
son propre identifiant (`LEGIARTI…`), avec sa période de validité, et les versions d'un
même article sont reliées par `VERSIONS/LIEN_ART`. Le stock global contient toutes ces
versions.

**L'historique éditorial est perdu.** La DILA réécrit le fichier d'un identifiant quand
elle fait évoluer son état ou corrige une erreur. Un fichier réécrit au même endroit
écrase l'état précédent. Un fichier réécrit dans l'autre arborescence (`en_vigueur` /
`non_vigueur`) laisse une copie résiduelle : l'arbitrage d'ADR-034 §1 la départage par
date et l'écarte. Quant à la base, chaque run la reconstruit à partir d'un seul stock :
elle ne contient qu'un instant.

Les 11 copies écartées (`superseded_copy`) du run `677e4cf0` (LEGI à 0,01 %), comparées
à la copie gardée :

| Changement (copie ancienne → récente) | Cas |
|---|---|
| L'abrogation différée prend effet : `ABROGE_DIFF` → `ABROGE`, rien d'autre ne change | 5 |
| La même chose sur la ligne `LIEN_ART` d'un article voisin | 2 |
| L'entrée en vigueur différée prend effet : `VIGUEUR_DIFF` → `VIGUEUR` | 1 |
| Le texte parent est abrogé : sa `fin` et l'état d'un article voisin changent | 1 |
| La DILA corrige les dates : `ABROGE_DIFF` 2023-12-30 → 2024-03-01 devient `VIGUEUR` à partir du 2024-03-01 | 1 |
| La DILA reconsolide l'article : texte et dates changent sous le même identifiant | 1 |

- **La copie la plus récente porte toujours l'état le plus avancé ou corrigé.** La
  copie ancienne porte un état `_DIFF` dans 9 cas sur 11 : c'est fréquent, mais ce
  n'est pas une règle.
- **Quand un état `_DIFF` se résout, la DILA réécrit le fichier la veille de la date
  d'effet.** Par exemple, `fin=2025-02-01` est réécrit le 2025-01-31.
- **Une reconsolidation change le texte sous le même identifiant.**
  LEGIARTI000006861064 était publié `VIGUEUR` de 1974 à 2999, avec un paragraphe 4.
  Depuis le 2024-02-19, il est `MODIFIE` de 1974 à 1976 et ne contient plus ce
  paragraphe : celui-ci est dans une nouvelle version, LEGIARTI000049158857
  (`ABROGE`, de 1976 à 2004). L'ancienne copie donnait en vigueur un arrêté abrogé en
  2004.

Sans historique éditorial, Murphy ne peut ni montrer ni prouver ce que la DILA publiait
à une date donnée, en particulier avant une correction. Or c'est ce qui protège
l'éditeur d'un outil public, si un utilisateur s'est fié à un texte depuis corrigé.

La DILA publie, en plus de ses stocks globaux, des **incrémentaux quotidiens** :
chacun contient les fichiers ajoutés ou réécrits et la liste des fichiers supprimés.
L'incrémental le plus ancien disponible date du 12 juillet 2025, et notre stock global
du 13 juillet 2025.

## Décision

**1. Deux historiques, jamais confondus.**

- **Historique juridique** : les versions d'un texte, chacune avec son identifiant et
  sa période de validité. Il dit ce qu'était le droit à une date donnée.
- **Historique éditorial** : les révisions d'un identifiant, c'est-à-dire ce que la
  DILA a publié pour cet identifiant, et à quelle date. Il dit ce que la DILA affirmait
  à une date donnée, erreurs comprises.

L'interface ne présente jamais une révision comme un état du droit. Une révision
remplacée s'affiche comme « publiée par la DILA le X, remplacée le Y ».

**2. Les archives brutes de la DILA font foi.** Le stock global et chaque incrémental
sont gardés tels que téléchargés, sans jamais être modifiés ni supprimés. Une empreinte
sha256 de chaque archive est relevée au téléchargement, et le dossier des archives est
sauvegardé hors de la machine. La base reste dérivée : on la reconstruit en rejouant les
archives, et `nuke_all` reste valable. Perdre la base coûte une reconstruction ; perdre
une archive coûte une preuve.

Le périmètre couvre toutes les sources DILA ingérées : elles publient toutes des
incrémentaux au même format.

**3. L'historique commence au plus tôt que les données permettent.**

- Pour la période couverte, le point de départ est le stock global du 13 juillet 2025,
  puis tous les incrémentaux disponibles depuis le 12 juillet 2025.
- Pour la période antérieure, seules les copies résiduelles du stock global sont
  disponibles. Elles deviennent des révisions, datées par leur mtime.

**4. L'ordre de rejeu.** Les archives sont rejouées dans l'ordre de l'horodatage que
porte leur nom. Dans le stock global, les copies d'une même racine sont ordonnées par
mtime (ADR-034 §1) ; à mtime égal, le parser refuse toujours le document
(`facet_root_duplicated`).

La date d'une révision est l'horodatage de l'archive qui l'apporte. Pour une révision
issue du stock global, c'est son mtime, car le stock ne date que sa propre photographie.
La provenance de la date est enregistrée (`archive` ou `mtime`), et l'interface signale
une date `mtime` comme approximative.

**5. Une révision est une copie complète.** Elle contient le document entier (texte,
état, dates, métadonnées), tel que publié, identifié par `(identifier, published_at)`,
avec sa provenance : l'archive, le chemin du fichier dans l'archive, son sha256 et la
provenance de la date.

- Les révisions vivent dans leur propre collection. `documents` garde la révision
  courante, et le backend, la recherche et le contrat ne changent pas pour elle.
- Une révision dont le contenu analysé est identique à la précédente n'est pas créée :
  l'archive qui la republie s'ajoute à ses provenances.
- Les différences entre révisions se calculent à l'affichage ; elles ne sont pas
  stockées.

**6. Seule la révision courante est indexée.** OpenSearch indexe la révision courante,
qui contient les corrections. Les révisions remplacées ne sont pas cherchables : elles
se consultent depuis l'onglet de leur document.

**7. Une suppression ferme l'historique.** Quand un incrémental supprime un fichier :

- le document quitte l'état courant (`documents`, OpenSearch) ;
- ses révisions restent ;
- une dernière révision, « supprimé par la DILA le X », ferme son historique.

**8. Une révision appartient à un seul identifiant.** Aucun lien vers d'autres
identifiants n'est stocké. L'interface relie les versions entre elles par les
`LIEN_ART` de la révision courante.

Pour LEGIARTI000006861064, sous l'ancienne révision : « remplacée le 2024-02-19 ;
versions de cet article aujourd'hui : 006861064 (1974-1976), 049158857 (1976-2004) ».

L'interface n'en déduit jamais un déplacement de texte (« le paragraphe 4 est passé
dans 049158857 ») : les `LIEN_ART` disent qu'une version existe, pas d'où vient son
texte. N'est affiché que ce que disent les fichiers de la DILA.

## Alternatives rejetées

- **La base fait foi** : ajouter chaque nouvel état dans une collection que `nuke_all`
  ne vide jamais. L'historique ne serait plus reconstructible, et un changement de
  parser ou de mapping demanderait de migrer une base irremplaçable.
- **Garder seulement la copie la plus récente** (l'arbitrage actuel) : les corrections
  de la DILA disparaissent sans trace, et Murphy ne peut plus prouver ce qui était
  publié avant.
- **Garder seulement l'historique des états** (`ETAT`, `DATE_DEBUT`, `DATE_FIN`) : une
  reconsolidation change aussi le texte, et l'ancien texte est précisément ce qu'il faut
  pouvoir montrer.
- **Stocker les différences plutôt que les copies complètes** : la lecture d'une
  révision dépendrait de toute la chaîne qui la précède, pour un gain de place faible
  sur des documents de quelques Ko.
- **Indexer toutes les révisions** : la recherche remonterait des textes que la DILA a
  corrigés.
- **Stocker un lien entre la révision corrigée et la nouvelle version** : ce serait une
  inférence, alors que les `LIEN_ART` donnent déjà les versions.
- **Dater toutes les révisions par mtime** : il dépend de l'extraction (`tar` le
  préserve, `cp` sans `-p` non) et ne date qu'une écriture de fichier. L'horodatage de
  l'archive est fixé par la DILA.

## Conséquences

- L'archivage des incrémentaux est la première tâche à mettre en place, avant toute
  ingestion : chaque jour d'incrémental que la DILA retire avant qu'on l'ait archivé est
  perdu pour toujours.
- Le stockage des archives devient critique : stockage en ajout seul, empreintes,
  sauvegarde hors de la machine.
- Une reconstruction complète rejoue le stock puis tous les incrémentaux : sa durée
  augmente d'un incrémental par jour. Elle est à mesurer (`statistics`, ADR-034 §8).
- Une collection de révisions s'ajoute à `MURPHY_DATA`. Sa taille est à mesurer.
- ADR-034 §1 est **amendé** : une copie écartée par l'arbitrage reste comptée comme
  collision, et devient en plus une révision datée par son mtime.
- Le connecteur ne lit plus seulement une arborescence : il rejoue des archives dans
  l'ordre, et applique leurs suppressions.
- L'interface (une vue des révisions dans l'onglet d'un document) et la route du
  backend qui les sert sont à concevoir, avec leur extension du contrat.

## Points ouverts

- Le sort d'un document supprimé dans Neo4j : son nœud et les relations qui
  l'atteignent.
- La forme de l'interface des révisions et de la route qui les sert.
- Le découpage en commits, à fixer au démarrage de la mise en œuvre.

## Références

ADR-005 (exhaustivité) · ADR-010 (base dérivée, serving stateless) · ADR-034 §1
(arbitrage des copies, amendé) et §8 (`MURPHY_META.collisions`, `statistics`) ·
`data/src/ragcore/sources/generic/copy_arbitration.py` ·
[sources.md](../../technical/data/reference/sources.md)
