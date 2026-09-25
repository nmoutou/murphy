# Taxonomie du droit français — registre des sources

> **Requalifié le 31 juillet 2026.** Ce registre ne sert plus à choisir une
> ossature : il recense le **matériau de peuplement et de falsification** du
> modèle décrit en [README.md](README.md).
>
> Le renversement tient à C6 (`SOCLE.md`) — **les nomenclatures ci-dessous
> qualifient des documents, quand la taxonomie qualifie des normes.** Elles ne
> peuvent donc pas la fonder : la théorie fournit les axes, les sources les
> peuplent et les éprouvent. Le §1 reste valide et gagne même en portée, à
> ceci près que ses sept entrées sont désormais lues comme des **facettes de
> document** (`FACETTES.md` §2), non comme des candidates à l'ossature.
>
> Les mentions de B-08, du golden-set et des douze strates sont **caduques**
> et conservées telles quelles : ce registre reste lisible comme le
> raisonnement qu'il était.

## 1. Le constat qui structure ce registre

**Il n'existe pas de taxonomie canonique du droit français.** Aucune source
ci-dessous ne dit « voici les branches du droit ». Ce qui existe, ce sont des
**nomenclatures opérationnelles**, chacune construite pour un usage précis, et
dont le découpage porte la marque de cet usage :

| Nomenclature | Construite pour | Ce que le découpage privilégie |
|---|---|---|
| Codes LEGI | Légiférer | La matière **écrite**, telle que le législateur l'a rassemblée |
| NAC | Enregistrer une affaire civile au greffe | L'**acte de saisine**, pas la question de droit |
| NATINF | Qualifier une infraction | Le **comportement punissable** |
| PCJA / plan judiciaire | Indexer une décision | Le **point de droit tranché** |
| Tables du CC | Analyser une jurisprudence | Le **fondement constitutionnel invoqué** |
| Jurisguide | Former un étudiant | La **discipline universitaire** |
| Service-public | Répondre à un usager | La **situation vécue** |

Conséquence pratique : le choix d'une ossature est une **prise de position**,
pas une lecture. C'est exactement la situation décrite en `WIP/B-08-cadrage.md`
§2 (problème *wicked* : la typologie ne peut pas être validée avant d'être
utilisée). Le registre ne tranche donc pas — il qualifie ce que chaque source
peut porter, et à quel coût.

Corollaire : les nomenclatures **judiciaires** (NAC, NATINF, PCJA) décrivent le
contentieux, donc surpondèrent mécaniquement ce pour quoi on saisit un juge.
C'est précisément le biais que `GOLDEN-SET.md` §6.1 neutralise en retenant S11
et S12 à 0 %. Une ossature bâtie sur ces seules sources reproduirait le biais.

## 2. Vocabulaire de statut

| Statut | Signification |
|---|---|
| ✅ | Source ouverte et vérifiée à la date indiquée ; le contenu annoncé a été constaté |
| 🟡 | Ouverte, mais **partiellement** exploitable — contenu dynamique, PDF lourd, ou périmètre à confirmer |
| ⬜ | Recensée, **non ouverte** |
| ✉️ | Demande à formuler (pas de contenu accessible en ligne) |

Toutes les vérifications ci-dessous datent du **2026-07-31** sauf mention.

---

## 3. Ossature — nomenclatures officielles

Les candidats sérieux au rôle de squelette de la taxonomie.

| Source | Apport taxonomique | Accès | Statut | Notes |
|---|---|---|---|---|
| **Légifrance — codes en vigueur** | **LEGI** — 1 code ≈ 1 matière ; hiérarchie code→partie→livre→titre→chapitre | https://www.legifrance.gouv.fr/liste/code?etatTexte=VIGUEUR | ✅ | **76 codes** affichés filtre `VIGUEUR` ; **108** tous états confondus (inclut abrogés et différés). Liste **plate et alphabétique** — aucun regroupement par branche : l'ossature est à construire, pas à recopier |
| **PCJA — plan de classement de la jurisprudence administrative** | **JADE** — le point de droit tranché, en administratif | https://www.legifrance.gouv.fr/ceta/planclassement | 🟡 | La **vraie** nomenclature administrative (l'entrée « ArianeWeb » du registre initial la visait sans la nommer). Rubriques numérotées alphabétiques : `01` Actes législatifs et administratifs, `02` Affichage et publicité, `03` Agriculture et forêts, `04` Aide sociale, `05` Alimentation, `06` Alsace-Moselle, `07` Amnistie/grâce, `08` Armées et défense, `09` Arts et lettres, `095` Asile, `10` Associations et fondations, `11` Associations syndicales… La numérotation `095` révèle des **insertions tardives** : plan historique, non rebâti. Arborescence dépliable **chargée dynamiquement** → non extractible par simple fetch |
| **Plan de classement de la jurisprudence judiciaire** | **CASS/INCA/CAPP** — pendant judiciaire du PCJA | https://www.legifrance.gouv.fr/juri/planclassement | 🟡 | Premier niveau = **juridictionnel, pas thématique** (Cassation civile / Cassation criminelle / Cour d'appel) ; le thématique est en dessous. Même limite technique : arbre dynamique |
| **NAC — nomenclature des affaires civiles** | Judiciaire civil/social/commercial — natures d'affaires | https://www.data.gouv.fr/datasets/nomenclatures-des-affaires-civiles-et-des-procedures-particulieres | ✅ | Ministère de la Justice, **Licence Ouverte 2.0**, MAJ **2026-06-25**. CSV (88 Ko) / JSON (298 Ko) / XLSX + **3 fichiers de documentation** (dont une notice PDF). Millésimes antérieurs conservés (2022, 2023, 2024) → utile pour la stabilité dans le temps. Structure à 3 niveaux annoncée dans la notice, **non confirmée depuis la page** |
| **NATINF — nomenclature des infractions** | Pénal — infractions pénales, douanières, fiscales | https://www.data.gouv.fr/datasets/liste-des-infractions-en-vigueur-de-la-nomenclature-natinf | ✅ | Ministère de la Justice, **LO 2.0**, MAJ **2026-06-05**, **trimestrielle**. 13 fichiers CSV (~4 Mo). Colonnes : n° NATINF, qualification (≤210 car.), nature/gravité, articles d'incrimination, articles de peine. ⚠️ **Aucune classification thématique native** — c'est une liste à plat d'infractions, pas un arbre. Un regroupement S1/S2 devra être **dérivé** (par code d'incrimination) |
| **Tables analytiques du Conseil constitutionnel** | **CONSTIT** — fondements constitutionnels | https://www.conseil-constitutionnel.fr/les-decisions/tables-analytiques | 🟡 | Titres de niveau 1 confirmés jusqu'à `15 Autorités indépendantes` (dont `1` Normes constitutionnelles, `2` Normes organiques, `3` Normes législatives et réglementaires, `4` Droits et libertés, `8` Élections et référendums nationaux). L'estimation « 16 titres » du registre initial n'est **pas infirmée**, non close. Table complète 1958-2024 (MAJ 31/12/2024) : PDF **40 Mo** — https://www.conseil-constitutionnel.fr/sites/default/files/2026-01/1958-202412_tables.pdf. Tables annuelles depuis 2009. **PDF uniquement, aucun format structuré** |
| **JUDILIBRE — endpoint `/taxonomy`** | CASS — **matières**, chambres, formations, solutions, en lecture machine | https://github.com/Cour-de-cassation/judilibre-search | 🟡 | La seule nomenclature du lot **directement requêtable en API**. Dépôt actif (661 commits, branche `dev`), API en **bêta** revendiquée. LO 2.0. Reste à faire : appeler `/taxonomy` et constater la liste réelle des matières |

## 4. Corpus et accès aux données

Pas des taxonomies — les gisements sur lesquels la taxonomie sera projetée.

| Source | Apport | Accès | Statut | Notes |
|---|---|---|---|---|
| DILA — OPENDATA (DTD, `dtd_map.xlsx`) | Toutes bases — DTD par base, champs XML | https://echanges.dila.gouv.fr/OPENDATA/ | ✅ | HTTP 200. Doc technique générique + table DTD×base. Contenu non inventorié |
| PISTE — API Légifrance | Toutes bases — accès programmatique | https://piste.gouv.fr | ✅ | HTTP 200. Gratuit après inscription. **Voie de contournement** des deux arbres dynamiques du §3 |
| data.gouv — LEGI | Codes, lois, règlements consolidés | https://www.data.gouv.fr/datasets/legi-codes-lois-et-reglements-consolides | ✅ | HTTP 200 |
| data.gouv — CASS | Arrêts publiés Cour de cassation | https://www.data.gouv.fr/datasets/cass | ✅ | HTTP 200 |
| data.gouv — INCA | Arrêts inédits Cour de cassation | https://www.data.gouv.fr/datasets/inca | ✅ | HTTP 200 |
| data.gouv — CAPP | Arrêts des cours d'appel | https://www.data.gouv.fr/datasets/capp | ✅ | HTTP 200 |
| data.gouv — JADE | Jurisprudence administrative | https://www.data.gouv.fr/datasets/jade | ✅ | HTTP 200 |
| **Service-public.fr — guide « Vos droits et démarches » (particuliers)** | **Registre citoyen** — le droit découpé en *situations vécues* | https://www.data.gouv.fr/datasets/service-public-fr-guide-vos-droits-et-demarches-particuliers | ✅ | DILA / Premier ministre, **LO 2.0**, **MAJ quotidienne**. XML 22,5 Mo. **Ajout proposé** : c'est la seule source qui découpe le droit du point de vue de l'usager — donc le pont naturel vers le registre `citoyen` (`GOLDEN-SET.md` §6.3), là où les 7 autres nomenclatures parlent le registre normatif. Schéma v3.5 (v3.3 arrêtée le 04/05/2026) |
| ArianeWeb (Conseil d'État) | JADE — interface de consultation | https://www.conseil-etat.fr/decisions-de-justice/jurisprudence/rechercher-une-decision-arianeweb | ✅ | ~300 000 décisions + analyses + conclusions. **Requalifié** : c'est un point d'accès, pas une source de nomenclature — voir PCJA au §3. Manuel utilisateur (2019) : https://www.conseil-etat.fr/arianeweb/static/pdf/ManuelutilisateurArianeWeb.pdf — c'est lui qui documente le PCJA (§4.4) |
| ~~OpenJustice specs~~ | — | https://github.com/Cour-de-cassation/openjustice-specs | ⚠️ **déprécié** | Le dépôt l'annonce lui-même : « les spécifications de l'API publique JUDILIBRE sont dorénavant maintenues au sein du projet **JUDILIBRE-search** ». 18 commits, 0 star. **Remplacé** par l'entrée JUDILIBRE du §3 |
| Contact données DILA | Doc de champ non publiée (FTPS) | donnees-dila@dila.gouv.fr | ✉️ | À solliciter seulement si le §4 ne suffit pas |

## 5. Se documenter — Jurisguide et doctrine

Ajout demandé. **Jurisguide** (jurisguide.fr, ex-`jurisguide.univ-paris1.fr`) est
le guide de recherche documentaire juridique des BU françaises, piloté par la
**BIU Cujas**. Rédigé pour des étudiants qui débutent — donc calibré exactement
pour un lecteur sans formation juridique.

| Source | Apport | Accès | Statut | Notes |
|---|---|---|---|---|
| **Fiches documentaires** (228) | **Ossature indirecte** : le facettage par domaine | https://www.jurisguide.fr/fiches-documentaires/ | ✅ | 228 fiches, facettées par **domaine du droit** (public, privé, international/européen, administratif, commercial, constitutionnel, pénal, travail, civil, environnement, fiscal, PI, famille, concurrence… + ~50 spécialisations : sport, énergie, maritime…), par **source** (doctrine / jurisprudence / législation), par **type** (revues, bases, codes, dictionnaires, encyclopédies) et par **support**. ⚠️ Cette liste de domaines est une **taxonomie universitaire de fait** — à confronter aux 12 strates : elle dira ce que le découpage statistique a écrasé |
| **Fiche « Méthodologie de la recherche documentaire en droit »** | Comment un juriste passe d'un fait à une matière | https://www.jurisguide.fr/fiches-pedagogiques/methodologie-de-la-recherche-documentaire-en-droit | ✅ | **La fiche la plus utile au projet.** Décrit la démarche exacte que le moteur doit imiter : analyser le sujet → **identifier le domaine juridique** (privé/public, quelle branche) → construire les mots-clés. Mentionne les langages documentaires contrôlés (thésaurus de bases, fichiers matière) et les identifiants **NOR / ELI / ECLI** — recoupe ADR-018 (identité ECLI). PDF téléchargeable |
| **Fiche « Codes juridiques — panorama »** | Ce qu'est un code, officiel vs éditeur | https://www.jurisguide.fr/fiches-pedagogiques/codes-juridiques-panorama/ | ✅ | Lue intégralement. Distingue **codes officiels** (DILA, loi+décret sans adjonction, issus de la Commission supérieure de codification) et **codes privés** (Dalloz « rouges », LexisNexis « bleus », Berger-Levrault, Éditions législatives…), sans valeur officielle mais qui **codifient des matières que l'État n'a pas codifiées** (ex. Code des sociétés, Code constitutionnel et des droits fondamentaux, Code des procédures collectives). Énumère **77 codes Légifrance** avec millésimes (cohérent avec les 76 constatés au §3). Explique la structure interne : parties L / R\* / D\* / R / D. PDF |
| Fiche « Moteurs de recherche et portails juridiques » | Cartographie des points d'accès | https://www.jurisguide.fr/fiches-pedagogiques/moteurs-de-recherche-et-portails-juridiques/ | ✅ | ~40 ressources (Légifrance, Service-public, Juricaf, GlobaLex, ISIDORE…), FR et étranger. Rédigée BIU Cujas 2016, **MAJ 2026-03-18**. PDF |
| Fiche documentaire « ArianeWeb » | Regard tiers sur le fonds administratif | https://www.jurisguide.fr/fiches-documentaires/arianeweb-1 | ⬜ | Repérée, non ouverte |
| **Plans de classement des encyclopédies** (Répertoires Dalloz, JurisClasseur) | **La taxonomie doctrinale** — le découpage que les juristes pratiquent | — | ⬜ | **Piste la plus prometteuse encore ouverte**, et la seule qui ne soit pas dictée par une contrainte de gestion. Les « Rép. civ. », « Rép. pén. » etc. ont un plan de classement par matière, stable depuis des décennies. ⚠️ **Accès payant** (Dalloz.fr, Lexis 360) — vérifier une éventuelle entrée par BU |

## 6. Ce que le registre ne couvre pas encore

Angles morts assumés, à ouvrir ou à écarter explicitement :

- **Droit de l'Union européenne et international** — aucune source au registre.
  EUR-Lex expose un *Répertoire de la législation* hiérarchisé (~20 chapitres) ;
  EuroVoc est un thésaurus multilingue. Hors périmètre DILA, mais S11
  (libertés publiques, données personnelles) est en pratique européanisé.
- **Droit du travail conventionnel** — les conventions collectives (base KALI)
  ne sont ni dans LEGI ni dans les nomenclatures ci-dessus, alors que S6 pèse
  4,13 %.
- **Articulation entre nomenclatures** — aucune table de correspondance publique
  NAC ↔ NATINF ↔ PCJA n'a été identifiée. Si l'ossature retenue croise plusieurs
  sources, la jointure sera **à construire à la main**, et c'est un coût à
  chiffrer avant de s'engager.
- **Stabilité temporelle** — seule la NAC publie ses millésimes antérieurs.
  Pour les autres, aucune garantie qu'un code de nomenclature signifie la même
  chose d'une année sur l'autre — à confronter à la **date pivot**
  (`GOLDEN-SET.md` §6.4).

## 7. Prochains pas suggérés

Par rapport coût/apport décroissant :

1. **Appeler `/taxonomy` de JUDILIBRE** — la seule nomenclature lisible par
   machine sans scraping ; quelques minutes.
2. **Télécharger NAC (JSON) et NATINF (CSV)** et constater les niveaux réels —
   les deux sont légers, sous LO 2.0, et la notice NAC est fournie.
3. **Extraire les deux plans de classement Légifrance** via PISTE plutôt que par
   le navigateur (les arbres HTML sont dynamiques).
4. **Relever le facettage « domaine du droit » des 228 fiches Jurisguide** et le
   confronter aux 12 strates — test de couverture à faible coût, et le seul qui
   vienne d'une source non judiciaire.
5. **Trancher l'accès aux plans Dalloz/JurisClasseur** (BU ?) — sinon écarter la
   piste explicitement plutôt que la laisser ouverte.
