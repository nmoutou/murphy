# Taxonomie du droit français

> **Statut : en construction, reparti de zéro le 31 juillet 2026.** Aucune
> continuité n'est recherchée avec les travaux antérieurs du projet — ni les
> douze strates, ni le socle statistique dont elles étaient tirées.

## 1. Ce que c'est

Un **instrument de classification interne, durable**, fonctionnant à la
manière d'une ontologie légère : des dimensions déduites, des relations
typées, des alignements explicites vers les nomenclatures existantes.

« Canonique » y signifie **juste, valide, cohérent** — et non « pivot
d'interopérabilité ». La différence n'est pas rhétorique : elle interdit de
fonder les axes sur ce qu'on observe des nomenclatures officielles, puisque
celles-ci portent la contingence de sept problèmes de gestion administrative.

## 2. La décision de méthode

**La théorie fournit les axes ; les sources peuplent et falsifient.**

C'est l'inversion de l'ordre suivi par la première rédaction de
[SOURCES.md](SOURCES.md), et elle est justifiée par C6 (`SOCLE.md`) : les
nomenclatures officielles **qualifient des documents**, quand la taxonomie
doit qualifier des **normes**. Elles ne pouvaient donc pas la fonder.

Conséquence directe et vérifiable : la sphère personnelle du domaine de
validité — *à qui la norme s'applique-t-elle ?* — est nommée par **aucune** des
sept sources et se déduit du socle en une ligne.

## 3. Périmètre

**Ce que le modèle porte :**

| Côté | Traitement | Mandat |
|---|---|---|
| **Norme** | **Extensionnel** — énumérable, exhaustivité visée et vérifiable | C1 |
| **Fait** | **Intensionnel** — types de situation seulement, catalogue ouvert, exhaustivité ni visée ni possible | C4 |

**Ce que le modèle ne porte pas, et ne doit jamais porter.** Critère de
démarcation, à opposer à toute extension future :

> Ce modèle ne doit **jamais pouvoir répondre à une question de droit**,
> seulement dire de quoi elle relève.

Sont donc exclus : le raisonnement juridique, les règles d'applicabilité
opérationnelles, l'inférence d'une solution, la modélisation FRBR des œuvres.
Cette frontière est ce qui distingue le présent chantier du volet doctoral
abandonné (ADR-001) — il ne le rouvre pas.

## 4. Index

| Fichier | Contenu |
|---|---|
| [SOCLE.md](SOCLE.md) | Les six certitudes C1–C6 et leurs développements. **Tout le reste en descend** |
| [FACETTES.md](FACETTES.md) | Registre des dimensions : admises, candidates, écartées. Critères d'admission |
| [RELATIONS.md](RELATIONS.md) | Registre des liens typés. Forme générale du modèle : arborescent localement, acentré globalement |
| [METHODE.md](METHODE.md) | Les trois tests, le moteur de la question orpheline, le journal des itérations |
| [SOURCES.md](SOURCES.md) | Registre des nomenclatures et corpus. **Matériau de peuplement et de falsification**, plus candidat à l'ossature |

## 5. État du modèle

| | |
|---|---|
| Certitudes | 6 (C1–C6) |
| Facettes de norme admises | 5 (F1–F5) |
| Facettes de document | 3 (D1–D3) |
| Candidates sous examen | 2 |
| Relations recensées | 6 admises, 4 candidates |
| Orphelines traitées | 3 |

## 6. Ce qui reste ouvert

Par ordre de conséquence décroissante.

| # | Question | Où |
|---|---|---|
| **1** | **La qualification est-elle une entité ou une relation ?** Le pénal pousse vers *entité* (liste fermée et publiée : NATINF), le civil vers *relation* (construite au cas par cas). Commande la présence ou l'absence d'un centre dans le modèle | `RELATIONS.md` R-01 |
| **2** | **L'ordre conditionnel** — la convention collective déroge à la loi si elle est plus favorable. Un rapport de rang qui dépend d'une comparaison de contenu, non exprimable comme ordre partiel statique | `RELATIONS.md` R-02 |
| **3** | **Les conditions** (qualité pour agir) sont-elles réductibles à des normes de fonction secondaire ? Hypothèse posée, test de falsification écrit | `RELATIONS.md` R-03 |
| **4** | **La modalité déontique** — facette conditionnelle sur F5, ou attribut de F5 ? | `FACETTES.md` F-01 |
| **5** | **Numérotation de C6** — retenu comme la distinction norme/document ; l'alternative était d'y promouvoir les quatre sphères de validité | `SOCLE.md` S-01 |
| **6** | **Construction de l'arbre de F1** — seul axe entièrement à bâtir, et seul dont aucune source ne soit non contingente | `FACETTES.md` F-02 |
