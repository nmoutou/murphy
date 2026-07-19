# ADR-028 — Frontière entre vérification automatique et validation humaine

**Statut** : Acté (19 juillet 2026, en préparation de B-04)

## Contexte

Les exigences de sortie (`EXIGENCES_v0.md`) demandent que chaque critère
soit « vérifié ». Le mot écrase deux questions de nature différente :

- **mécanique** — *le système calcule-t-il correctement la formule qu'on
  lui a donnée ?* Entrée → sortie déterministe (ex. nDCG@R, diff de
  `doc_id`). Un oracle indépendant tranche.
- **sémantique** — *la métrique mesure-t-elle la bonne chose ? ce grade
  0–3 est-il juste ? cette citation vaut-elle un jugement de
  pertinence ?* Question ouverte : **produire l'oracle, ce serait
  répondre à la question**.

Fabriquer un test automatique pour une question sémantique est une
**tautologie** : il verrouille l'hypothèse au lieu de la valider, et
donne une fausse assurance. Certaines validations sont irréductiblement
humaines — le porteur en v0, des experts en alpha/beta.

## Décision

Toute exigence relève de l'un de **trois régimes de vérification**. Le
critère de tri est la **nature de la question**, jamais le projet (P1/P2)
ni l'outil disponible.

| Régime | Nature | Qui vérifie |
|---|---|---|
| **auto** | Question mécanique fermée, oracle déterministe, aucun jugement | La machine (test/CI) |
| **assisté** | La machine produit un **candidat** ; un humain **tranche** | Machine + humain (porteur v0, expert ensuite) |
| **humain** | Jugement sémantique irréductible ; l'oracle *est* la réponse | Humain seul (porteur v0, experts alpha/beta) |

**Règle anti-tautologie.** On ne construit jamais d'oracle automatique
pour une question sémantique. En régime **assisté**, une sortie machine
est un **candidat, jamais une vérité terrain** : le code qui la produit
ne la valide pas.

Deux confusions nommées explicitement, parce qu'elles sont le vrai
piège :

- **E-P2-05 (qrels citation-minées)** — « produit par du code » ne veut
  pas dire « validé ». Miner les paires (citante, citée) du graphe est
  **auto** ; poser que *citation ≈ pertinence* est une **hypothèse**
  (régime assisté), pas une vérité terrain. C'est précisément la raison
  d'être des strates (ADR-017 : strate 2 = garde-fou, pas jugement).
- **E-P2-10 (baseline reproductible)** — la **reproductibilité** (diff
  des métriques nul) est **auto** ; la **justesse** du chiffre n'est pas
  dans le périmètre v0 et ne se teste pas mécaniquement. Reproductible
  n'est pas juste.

Corollaire pour le scorer (B-04, E-P2-02/03) : il est **auto pur** —
ADR-006 l'a voulu « trivial et neutre » exactement pour qu'aucun jugement
n'y vive. Son test se fait contre des cas jouets vérifiables à la main
par un tiers, sans oracle externe qui ne ferait que déplacer le risque.
La zone humaine est en **amont** (golden-set, grades) et en **aval** (le
classement a-t-il un sens juridique), pas dans le scorer.

## Alternatives rejetées

- **Deux régimes (auto / humain)** : range l'« assisté » dans « humain »
  et efface la distinction qui porte le risque le plus sournois —
  E-P2-05 aurait l'air aussi « humain » que le golden-set, masquant que
  le piège y est différent (une sortie machine qu'on prend pour une
  vérité).
- **Tout automatiser** : conduit à tester l'évaluation par
  elle-même — la tautologie qu'on refuse.

## Conséquences

- `EXIGENCES_v0.md` porte une colonne **Régime** (auto / assisté /
  humain) par exigence, référençant cet ADR. La colonne survit au fond,
  pas à la version : le principe est pérenne, l'étiquetage se rejoue à
  chaque version.
- Une exigence **humaine** ou **assistée** n'est jamais close par un
  « test vert » : sa clôture consigne **qui** a validé et **quand**
  (porteur v0 ; experts alpha/beta), conformément à `PILOTAGE.md` §3.
- Aligne avec ADR-017 : strate 1 = auto, strate 2 = hypothèse minée
  (assisté), strate 4 = jugement humain.

## Références

ADR-017 (strates 1/2–4) · ADR-006 · ADR-007 · ADR-016 ·
`EXIGENCES_v0.md` · `PILOTAGE.md` §3
