# Registre des risques - Murphy

*Phase 0 - cadrage stratégique. Ce que la note de cadrage décide, ce registre le met à l'épreuve : il porte ce qui invaliderait ces décisions.*

---

## 1. Hypothèses

Une hypothèse est un énoncé **non vérifié, falsifiable, et dont la fausseté déferait une décision**. Elle n'est pas un risque : un risque se surveille, une hypothèse se teste. Elles sont dérivées de la note de cadrage, dans son ordre.

| N° | Hypothèse | Si elle est fausse | Risque |
|---|---|---|---|
| **H-01** | L'obstacle est le **nommage**, non la lecture : atteindre la source suffit à débloquer celui qui ne savait pas la chercher. | Murphy résout un problème qui n'était pas le problème, pour une partie de sa cible. | R-01 |
| **H-02** | Il existe un public qui a besoin de la source, n'a pas accès à la couche éditoriale payante, et est **atteignable**. | Le public visé est soit inexistant, soit hors de portée : §1 décrit un manque que personne ne vient combler. | R-23 |
| **H-03** | Un **seul** système sert les groupes A et B sans que servir l'un dégrade l'autre. | **D-01** n'est pas tenable : il faut choisir un groupe, ou construire deux produits. | R-05 |
| **H-04** | L'usager **sait juger seul** si un document le concerne. | **D-07** confie un rôle que l'usager ne peut pas tenir. Toute la valeur de §3 repose dessus. | R-02 |
| **H-05** | La langue naturelle fonctionne comme **équation de recherche** : une reformulation déplace l'ensemble de façon prévisible par l'usager. | L'usager ne pilote pas, il tâtonne. L'« ensemble atteignable » de §3 n'a pas d'unité. | R-04 |
| **H-06** | Le **sans-état** ne coûte rien à la qualité : un tour qui porte tout son contexte vaut un tour qui hérite du précédent. | **D-06** est un coût de qualité, non une forme propre. | R-22 |
| **H-07** | Les gestes de pilotage sont **mesurables** : l'ensemble atteignable et le nombre de gestes pour l'atteindre se mesurent sur une collection de test. | **D-02(a)** ne mesure que le premier tour, c'est-à-dire pas le produit tel que §3 le définit. | R-13 |
| **H-08** | Sur une tâche réelle, Murphy fait **mieux que le contrefactuel** - moteur public, moteur généraliste, assistant conversationnel grand public. | **D-02(b)** échoue : le produit est correct et inutile. | R-03 |
| **H-09** | L'**anonymisation d'entrée ne dégrade pas la récupération** : ce qui identifie une personne n'a pas de valeur de recherche sur un corpus de droit général. | **D-09** est un arbitrage entre vie privée et qualité, et non plus un gain sans contrepartie. | R-19 |
| **H-10** | Le **refus explicite est acceptable** dès lors que l'élargissement existe : un usager à qui l'on ne rend rien reformule au lieu de partir. | Le refus est une impasse vécue, pas un plancher de non-fabrication. | R-04 |
| **H-11** | Les **identifiants du producteur** suffisent à fonder une identité canonique vérifiable de bout en bout. | La capacité d'identité opposable de §4 n'est pas atteignable sans appareil éditorial propre. | R-07 |
| **H-12** | La **quasi-totalité de l'architecture définitive** est constructible en T0, sans utilisateurs et sans argent. | T1 doit rattraper de l'architecture au moment où les tiers arrivent - ce que §5 pose comme impossible. | R-24 |
| **H-13** | Une **structure porteuse et un financement** sont trouvables au terme de T1. | Le seuil de sortie de T1 est infranchissable : T2 n'existe pas. | R-28 |
| **H-14** | La liste des données personnelles de T1 **reste close et courte**. | La minimisation cesse d'être une propriété d'architecture et redevient une promesse. | R-20 |

## 2. Contraintes

Une contrainte est **déjà vraie et ne se négocie pas**. Elle n'entre pas au registre : elle en délimite le terrain, et c'est en cherchant à s'en affranchir qu'on fabrique des risques.

| N° | Contrainte | Ce qu'elle rend non négociable |
|---|---|---|
| **C-01** | Le corpus est produit et diffusé par des tiers (**PP-01**, **PP-02**), chacun maître de ce qu'il publie et à quel rythme. | Ni le contenu, ni la fraîcheur, ni le format ne sont sous contrôle. Aucune complétude ne peut être promise. |
| **C-02** | Le conseil et la qualification juridique sont **monopolisés** (**PP-05**). | **D-03** n'est pas un choix de produit : c'est la borne légale, et elle vaut aussi pour ce que le service *paraît* faire. |
| **C-03** | Le RGPD s'applique **des deux côtés** - personnes citées dans le corpus, usagers du service (**PP-06**). AIPD obligatoire au seuil T0. | Le dossier de conformité doit être produisible à tout moment, y compris quand le service n'a qu'un utilisateur. |
| **C-04** | L'AI Act s'applique ; la catégorie du système **n'est pas déterminée** (**PP-07**). | La charge de conformité est inconnue tant que la qualification n'est pas faite. Elle ne peut pas être budgétée. |
| **C-05** | Un seul acteur conçoit, décide et exécute (**PP-13**). Aucune structure, aucun financeur (**PP-14**). | Aucune tâche ne se délègue, aucune décision ne se fait contredire, aucun coût ne se transfère. |
| **C-06** | Aucun budget en T0. | Tout ce qui exige de l'argent - annotateurs, hébergement, conseil juridique - est hors T0 par construction, non par arbitrage. |
| **C-07** | Aucune date n'est imposée de l'extérieur ; les jalons sont définis par des seuils (§5). | Il n'existe pas de « risque de retard » : ce que le calendrier ferait ailleurs, rien ne le fait ici. Voir **R-30**. |

## 3. Ce qui entre au registre

**Un risque a trois membres** : une cause **déjà vraie**, un événement **incertain**, une conséquence **sur la valeur ou sur une personne**. Un énoncé qui n'a pas les trois est un thème, et ne se surveille pas.

**Ce qui n'entre pas** : une hypothèse (§1), une contrainte (§2), un problème déjà survenu - qui relève de la conduite courante, pas de la surveillance.

**Porteur du risque.** Le registre ne distingue pas seulement ce que le projet subit :

- **projet** - la conséquence tombe sur le projet ;
- **usager** - la conséquence tombe sur celui qui s'en sert ;
- **tiers** - la conséquence tombe sur quelqu'un qui n'a rien demandé (une personne citée dans une décision, notamment).

**Gravité**, définie dans les termes du projet, faute de budget et de calendrier à mettre en jeu :

- **critique** - remet en cause une décision `D-xx`, ou interdit un seuil de jalon ;
- **majeur** - coûte une capacité de §4 « Dedans », ou une phase entière ;
- **mineur** - coûte du travail, pas une décision.

**Aucune cotation numérique.** Multiplier une probabilité par un impact produit un nombre qui n'a pas de sens et un classement qui a l'air d'un calcul. Le tri se fait sur la gravité et sur l'**échéance de décision** - le moment après lequel il est trop tard pour agir -, portée dans la réponse.

**Signal.** Chaque risque porte l'observable qui dirait qu'il se produit. Un risque sans signal n'est pas surveillé : il est seulement écrit.

## 4. Cartographie T0 / T1 / T2

| N° | Risque | Porteur | Gravité | T0 | T1 | T2 |
|---|---|---|---|---|---|---|
| **R-01** | Le problème visé n'est pas le problème réel | projet | critique | ○ | ● | ● |
| **R-02** | L'usager ne sait pas juger la pertinence | usager | critique | ○ | ● | ● |
| **R-03** | Le contrefactuel suffit déjà | projet | critique | ○ | ● | ● |
| **R-04** | L'usage dérive vers la question-réponse | usager | majeur | | ● | ● |
| **R-05** | Le service sert le mieux ceux qui savaient déjà chercher | usager | majeur | ○ | ● | ● |
| **R-06** | Rupture ou restriction de la diffusion ouverte | projet | critique | ● | ● | ● |
| **R-07** | Corpus incomplet, périmé, ou sans identité vérifiable | usager | majeur | ● | ● | ● |
| **R-08** | Indisponibilité du modèle de représentation | projet | mineur | ● | ● | ● |
| **R-09** | Coût d'exploitation incompatible avec la gratuité | projet | critique | ○ | ● | ● |
| **R-10** | Aucune collection de test crédible | projet | critique | ● | ● | ● |
| **R-11** | Annotateurs introuvables ou non finançables | projet | critique | ● | ● | ○ |
| **R-12** | Jugements de pertinence instables | projet | majeur | ● | ● | ○ |
| **R-13** | Le silence ne se mesure pas | projet | majeur | ● | ● | ● |
| **R-14** | Surajustement à la collection de test | projet | majeur | ● | ● | ● |
| **R-15** | Requalification en conseil juridique | projet | critique | ○ | ● | ● |
| **R-16** | La génération résiduelle n'est pas retirée | projet | critique | ● | ● | |
| **R-17** | Classification AI Act défavorable | projet | critique | ○ | ● | ● |
| **R-18** | Ré-identification de personnes citées dans le corpus | tiers | critique | ● | ● | ● |
| **R-19** | Anonymisation d'entrée défaillante, dans un sens ou dans l'autre | usager | majeur | ● | ● | ● |
| **R-20** | Rupture d'injointabilité par une trace involontaire | usager | critique | ● | ● | ● |
| **R-21** | Dommage subi par un usager qui a agi sur le résultat | usager | critique | | ● | ● |
| **R-22** | Aucune observation de l'échec de l'usager | projet | majeur | ○ | ● | ● |
| **R-23** | Les structures relais ne s'engagent pas | projet | critique | ○ | ● | ● |
| **R-24** | Ouverture sans capacité d'incident ni de support | projet | majeur | ○ | ○ | ● |
| **R-25** | La place est occupée avant l'ouverture | projet | mineur | | ○ | ● |
| **R-26** | Interruption du porteur | projet | critique | ● | ● | ● |
| **R-27** | L'arbitre est l'exécutant : aucune contradiction | projet | critique | ● | ● | ● |
| **R-28** | Ni structure ni financement au seuil de T1 | projet | critique | ○ | ● | |
| **R-29** | Élargissement du périmètre par facilité technique | projet | majeur | ● | ● | ● |
| **R-30** | T0 sans fin : rien d'extérieur n'oblige à sortir | projet | critique | ● | ○ | |

**Légende** : **●** actif - le risque peut se réaliser dans ce régime · **○** latent - la cause s'y constitue, l'effet vient plus tard · **case vide** - sans objet.

**La colonne T0 est plus pleine qu'on ne l'attend d'un régime sans utilisateur.** C'est la conséquence directe de §5 : T0 porte la quasi-totalité de l'architecture définitive, donc la quasi-totalité des façons de la manquer.

## 5. Les risques

### 5.1 Valeur et problème

| N° | Énoncé | Signal | Réponse |
|---|---|---|---|
| **R-01** | *Le moteur public exige le vocabulaire de la réponse* (§1) ; il se peut que ce vocabulaire ne soit pas le seul obstacle - un usager du groupe B qui reçoit le bon article ne sait pas davantage quoi en faire - et **Murphy résout alors un problème qui n'est pas celui de sa cible** (**H-01**). | Sur tâche réelle : la source pertinente est atteinte, la tâche n'aboutit pas. | Réduire. **D-02(b)** mesure le *taux de tâches abouties* et non la seule atteinte de la source : l'instrument de détection existe déjà. À trancher avant le seuil de T1 - soit le périmètre s'étend au-delà de la restitution (contre **D-03**), soit le groupe B sort de la cible (contre **D-01**). Aucun des deux ne se décide sans la mesure. |
| **R-02** | *§3 suppose que l'usager sait juger seul si un document le concerne* ; il se peut qu'une partie du groupe B ne le sache pas, et **le silence est alors lu comme « la règle n'existe pas »** - exactement l'impasse que §1 dénonce, reproduite à l'intérieur du produit. | Sur tâche réelle : conclusions fausses tirées d'un ensemble incomplet ; arrêt de la recherche après un ensemble vide. | Réduire. Le refus explicite et l'élargissement (§4) sont les deux contre-feux déjà décidés : un ensemble vide doit dire quoi reformuler, jamais rien. Reste à trancher avant T1 : **ce que le système dit de ce qu'il n'a pas trouvé**. Accepté comme risque résiduel - **D-07** est une décision, pas une ignorance. |
| **R-03** | *Le contrefactuel est gratuit et déjà installé* ; il se peut qu'il suffise à la cible - un assistant grand public rend une réponse plausible et une référence, ce qui satisfait sans être exact - et **le produit est alors correct et inutile** (**H-08**). | Sur tâche réelle : temps jusqu'à la première source pertinente comparable au contrefactuel, ou usagers qui retournent à leur outil habituel. | Réduire, par le seul avantage non copiable : l'identité canonique vérifiable de chaque source (§4). Décision au seuil de T1 - si **D-02(b)** ne montre aucun écart, T2 ne s'ouvre pas. |
| **R-04** | *L'usager arrive avec une question* ; il se peut qu'il lise l'ensemble restitué comme une réponse et le premier document comme la bonne réponse, et **le produit est alors utilisé comme ce que D-03 refuse d'être**, sans qu'aucune ligne de code l'ait promis. | Retours d'usage citant « la réponse de Murphy » ; abandon après le premier document ; aucun geste d'élargissement observé. | Réduire par la forme de la restitution - un ensemble se présente comme un ensemble. Objet du cahier des charges fonctionnel (phase 1) : les gestes de pilotage sont la réponse structurelle à ce risque. |
| **R-05** | *Aucun usager n'est écarté (**D-01**) et le résultat ne dépend pas du demandeur (**D-06**)* ; il se peut qu'un même système ne serve bien que ceux qui formulent déjà comme le corpus se formule, et **l'écart de §1 se reproduit alors à l'intérieur du produit** (**H-03**). | Écart de qualité entre requêtes du groupe A et du groupe B sur la collection de test, dès qu'elle distingue les deux. | Réduire. La collection de test doit porter les deux registres de formulation dès sa v1, faute de quoi le risque est invisible. Condition de conception, à poser en phase 3. |

### 5.2 Corpus et amont

| N° | Énoncé | Signal | Réponse |
|---|---|---|---|
| **R-06** | *Le corpus vient de tiers souverains (**C-01**)* ; il se peut qu'un producteur restreigne sa diffusion, change de format, de canal ou de licence, et **une partie du corpus devient alors inexploitable sans recours**. | Annonce de changement de format ou de licence ; rupture d'un canal de récupération. | Accepter, et instrumenter : chaque source doit être remplaçable indépendamment des autres, et la perte d'une base doit être un périmètre en moins, jamais un service arrêté. |
| **R-07** | *Le corpus est consolidé et daté par son producteur* ; il se peut qu'une version périmée, une abrogation manquée ou un identifiant instable soit restitué comme droit en vigueur, et **l'usager fonde alors une décision sur une règle qui n'existe plus**. Plus grave qu'un silence : une source périmée est crue. | Écart entre l'état du droit restitué et l'état publié, à date de contrôle ; identifiants qui ne résolvent plus chez le producteur. | Réduire. L'identité canonique vérifiable (§4) est déjà la réponse de principe : elle rend l'écart constatable par l'usager lui-même. À trancher en phase 2 : la politique de fraîcheur et de versionnage. |
| **R-08** | *Le modèle de représentation est fourni par un tiers (**PP-03**)* ; il se peut qu'il disparaisse ou change de licence, et **le corpus doit alors être ré-encodé en entier**. | Changement de licence ou retrait de publication. | **Accepté explicitement.** Le coût est connu, borné, et n'engage aucune décision : c'est du travail, pas un arbitrage. Aucune action avant que l'événement survienne. |
| **R-09** | *Le service est gratuit pour l'usager et son coût marginal n'est pas nul* ; il se peut qu'aucun modèle ne couvre l'exploitation (**PP-04**, **C-06**), et **la gratuité devient alors la raison pour laquelle le service ferme**. | Coût par requête projeté sur une volumétrie d'ouverture, comparé à tout financement identifié. | Réduire, et **trancher avant le seuil de T1** : le modèle économique est une condition de la structure porteuse (**H-13**), pas une question de T2. Le calcul se fait en T0, où il ne coûte rien. |

### 5.3 Récupération et mesure

| N° | Énoncé | Signal | Réponse |
|---|---|---|---|
| **R-10** | *La qualité de la récupération **est** la qualité du produit (§3)* ; il se peut qu'aucune collection de test crédible ne se constitue, et **on ne sait alors pas si le produit est bon** - ni s'il s'améliore. | Décisions techniques arbitrées sans mesure ; « ça a l'air mieux » comme critère. | Éviter. **D-02(a)** est le premier plan constructible : sans collection, la phase 3 n'a pas de sortie et T1 n'a pas de seuil. Aucune ouverture ne se prononce sur une intuition. |
| **R-11** | *Les jugements de pertinence exigent des juristes (**PP-11**, rôle inexistant à ce jour)* ; il se peut qu'ils soient introuvables ou non finançables (**C-06**), et **R-10 se réalise alors par manque de bras et non par manque de méthode**. | Recrutement d'annotateurs sans réponse ; annotation entièrement portée par le porteur. | Réduire. Constituer une collection amorce annotable par le porteur seul, et réserver l'annotation experte à ce qu'elle seule peut trancher. À arbitrer en phase 3 : le partage exact entre les deux. |
| **R-12** | *La pertinence juridique n'a pas de vérité unique* ; il se peut que deux annotateurs qualifiés divergent durablement, et **la mesure existe alors sans rien mesurer**. | Accord inter-annotateur bas et non réductible par le guide. | Réduire par le guide annotateur et une mesure d'accord dès la v1 de la collection. Si la divergence persiste, elle est un résultat : elle dit que la tâche n'a pas de cible unique, et cela change la définition de la valeur. |
| **R-13** | *Le silence est un mode d'échec de rang égal au bruit (§3)* ; il se peut qu'on ne sache mesurer que ce qui a été restitué - ce qui manque n'ayant jamais été jugé -, et **le registre de mesure ne couvre alors qu'un des deux modes d'échec** (**H-07**). | Le plan d'évaluation ne produit que des mesures de précision. | Réduire. Le problème est connu et ancien ; il se traite à la constitution de la collection, pas après. Contrainte de conception à poser en phase 3, avec les seuils go/no-go. |
| **R-14** | *La collection est le seul juge disponible* ; il se peut qu'on optimise ce qu'elle mesure plutôt que ce qu'elle représente, et **le produit progresse alors sur la mesure et nulle part ailleurs**. | Progression continue sur la collection sans effet sur **D-02(b)**. | Réduire : une part de la collection reste non exploitée pour l'optimisation, et **D-02(b)** est le contrôle externe. C'est la raison d'être des deux plans de rang égal de **D-02**. |

### 5.4 Juridique et conformité

| N° | Énoncé | Signal | Réponse |
|---|---|---|---|
| **R-15** | *Le conseil et la qualification sont monopolisés (**C-02**)* ; il se peut que le service soit lu comme qualifiant une situation - par sa présentation, par ses formulations, ou par ce que l'usage en fait (**R-04**) -, et **le projet se place alors sous une interdiction professionnelle**. | Formulation d'interface qui sélectionne « pour votre cas » ; retours d'usagers décrivant Murphy comme un conseil. | Éviter. **D-03** et **D-04** sont la position tenue ; ce qui reste à faire est de la rendre lisible dans l'objet lui-même, pas seulement dans un avertissement. Revue avant tout accès de tiers (seuil de T0). |
| **R-16** | *La génération de texte est « borderline interdite et destinée au retrait » (**D-04**)* ; tant qu'elle n'est pas retirée, il se peut qu'elle produise une formulation qui qualifie, et **c'est alors le seul composant du système capable de réaliser R-15 tout seul**. | Toute sortie contenant un mot de texte absent du corpus. | Éviter. Le retrait est décidé ; il reste à le dater. **Échéance : avant le seuil de sortie de T0** - aucun tiers ne doit atteindre un système qui génère. |
| **R-17** | *La catégorie AI Act du système n'est pas déterminée (**C-04**)* ; il se peut qu'elle soit défavorable - un usage en série sur des décisions engageantes se discute -, et **la charge de conformité devient alors sans commune mesure avec un porteur seul**. | Publication de lignes directrices ou de doctrine visant les systèmes de recherche juridique. | Réduire par la qualification anticipée : elle est transverse à toutes les phases (README) et se fait en T0, où elle ne coûte que du temps. Une catégorie défavorable connue tôt est un périmètre à réduire ; découverte tard, c'est un arrêt. |
| **R-18** | *La jurisprudence contient des personnes, pseudonymisées par leur producteur pour une lecture unitaire* ; il se peut que la recherche sémantique permette le recoupement que la lecture unitaire empêchait, et **le service ré-identifie alors des personnes qui n'ont rien demandé** (**PP-06**). | Requêtes rendant un ensemble qui converge sur une personne plutôt que sur une règle. | Réduire, et **traiter en T0** : c'est le premier risque du registre porté par des tiers, et le seul dont l'AIPD fera un objet propre. **D-09** ne protège pas de celui-ci - il porte sur la requête, pas sur le corpus. |
| **R-19** | *L'anonymisation d'entrée est *fail-closed* (**D-09**)* ; il se peut qu'elle échoue dans un sens - laisser passer une donnée identifiante - ou dans l'autre - refuser des requêtes légitimes qui nomment des personnes -, et **le système est alors soit poreux, soit inutilisable sur une part du besoin réel** (**H-09**). | Taux de refus d'anonymisation ; requêtes légitimes refusées en série ; données identifiantes retrouvées en aval. | Réduire. Le refus doit dire quoi reformuler (§4). Mesurer les deux sens dès T0, où le porteur est le seul usager et où l'échec ne coûte rien. |
| **R-20** | *L'injointabilité n'existe que si aucune trace du couple compte↔session n'est écrite (**D-08**)* ; il se peut qu'une seule trace involontaire - journal, débogage, sauvegarde - l'écrive, et **tout l'aval devient alors nominatif par une seule jointure**. Une occurrence suffit, et elle ne s'annule pas. | Toute écriture nouvelle contenant à la fois un identifiant de compte et un identifiant de session. | Éviter. La note l'anticipe déjà (§4, bornes d'exécution) ; il reste à en faire un point de contrôle explicite de revue de code et de revue d'exploitation, avant T1. |
| **R-21** | *L'usager est opérateur et garant de sa recherche (**D-07**)* ; il se peut qu'il subisse un dommage - délai manqué, droit non exercé - après avoir agi sur un ensemble incomplet, et **la responsabilité se discute alors quelle que soit la rédaction des avertissements**. | Premier signalement d'un usager décrivant un préjudice. | Réduire par ce qui est déjà décidé - non-interprétation, refus explicite, identité vérifiable des sources - et par l'avertissement, qui limite sans exonérer. **À expertiser avant le seuil de T1**, avec la question de la structure porteuse : c'est elle qui portera le risque, ou une personne physique. |

### 5.5 Usage et exposition

| N° | Énoncé | Signal | Réponse |
|---|---|---|---|
| **R-22** | *Le service est sans état et injointable (**D-06**, **D-08**)* ; il se peut qu'aucune observation ne permette de voir un usager échouer, et **le plan (b) de D-02 devient alors non instrumentable depuis le produit** (**H-06**). | Aucune donnée disponible pour établir un taux de tâches abouties. | Réduire, hors du système : la tâche réelle s'observe en protocole - avec **PP-10** et **PP-12** -, jamais par la télémétrie. C'est une conséquence assumée de **D-06**, à concevoir en phase 3 et non à corriger en T1. |
| **R-23** | *Les structures relais tiennent l'accès physique au groupe B (**PP-10**)* ; il se peut qu'elles ne s'engagent pas - charge, prudence, absence d'interlocuteur -, et **le groupe B n'est alors ni atteignable ni observable** (**H-02**), ce qui réalise R-22 par un autre chemin. | Aucun partenariat établi à l'approche du seuil de T0. | Réduire. L'intérêt est objectivement convergent (**PP-10**) ; ce qui manque est le contact, qui ne coûte rien en T0 et se prend tôt. Un pilote sans groupe B ne mesure que le groupe A - à acter comme tel si l'engagement n'arrive pas. |
| **R-24** | *T2 ouvre l'accès sans restriction* ; il se peut que rien ne soit prévu pour recevoir un incident, une réclamation, une demande d'accès ou un afflux, et **l'ouverture crée alors des obligations que personne ne peut tenir** (**H-12**). | Seuil de sortie de T1 atteint sans procédure d'incident éprouvée. | Réduire en T1, qui est précisément le régime où l'appareil de conformité doit être *exercé* et non plus écrit (§5). Condition de sortie de T1, à formuler à sa revue. |
| **R-25** | *L'écart de §1 est visible par d'autres* ; il se peut qu'un acteur financé (**PP-09**) ou un producteur public occupe la place avant l'ouverture, et **le projet perd alors sa raison d'être** - ce qui est un succès du point de vue du problème posé. | Annonce d'un service public ou gratuit couvrant le même geste. | **Accepté explicitement.** Le but est que le problème de §1 cesse d'exister, pas que Murphy existe. Aucune action défensive. |

### 5.6 Tenue du projet

| N° | Énoncé | Signal | Réponse |
|---|---|---|---|
| **R-26** | *Un seul acteur conçoit, décide et exécute (**C-05**)* ; il se peut qu'il s'interrompe, et **rien ne continue** - ni le service, ni la conformité, ni les obligations prises envers des tiers en T1. | Aucun. C'est un risque sans signal préalable, et c'est ce qui le rend critique. | Réduire ce qui est réductible sans second acteur : tout ce qui est décidé est écrit, et le dossier de conformité est produisible à tout moment (§5). Le reste est **accepté** : il n'existe aucune parade à **C-05** en T0. À rouvrir au seuil de T1 - accueillir des tiers sans relève est une obligation qu'on ne peut pas garantir. |
| **R-27** | *L'arbitre est l'exécutant (**PP-13**, **C-05**)* ; il se peut qu'aucune décision `D-xx` ne rencontre jamais de contradiction, et **les erreurs de cadrage survivent alors intactes** jusqu'à ce qu'un tiers les rencontre. Ce registre est lui-même écrit par la partie qu'il juge. | Aucune décision révisée sur une longue période ; hypothèses de §1 jamais mises à l'épreuve. | Réduire par des contradicteurs externes - annotateurs (**PP-11**), structures relais (**PP-10**), revue par un tiers du dossier de conformité. Aucun ne coûte d'argent. **À faire en T0**, pendant que les décisions sont encore révisables. |
| **R-28** | *Le seuil de sortie de T1 exige une structure porteuse financée* ; il se peut qu'elle ne se monte pas (**PP-14**, **H-13**), et **T2 n'existe alors jamais** - le service reste à accès restreint, indéfiniment. | Aucune démarche engagée à mi-parcours de T1 ; **R-09** sans réponse. | Réduire, en commençant en T0 ce qui ne demande pas d'argent : forme juridique, interlocuteurs, dossier. C'est le seul risque dont la réalisation est *silencieuse* - rien ne casse, la phase dure. |
| **R-29** | *Le système saura faire plus que ce que le périmètre autorise* ; il se peut qu'une capacité disponible soit activée parce qu'elle est là - la génération au premier chef (**D-04**) -, et **le périmètre se déplace alors sans décision**, contre **D-05**. | Toute fonction en service qui n'est rattachée à aucune ligne de §4 « Dedans ». | Éviter. Le périmètre est fixé par fonctionnalité, capacité ou source (**D-05**) : ce qui n'y figure pas ne s'active pas, même si cela ne coûte rien. Contrôle à chaque revue de jalon. |
| **R-30** | *Aucune date n'est imposée de l'extérieur (**C-07**) et aucun financeur n'exige de résultat* ; il se peut que le seuil de sortie de T0 ne soit jamais prononcé - il y a toujours une pièce à finir -, et **le projet ne rencontre alors jamais un tiers**, ce qui est l'unique façon dont il peut échouer sans jamais s'arrêter. | Le seuil de T0 réputé « presque atteint » sur deux revues successives. | Réduire. Le seuil de sortie de T0 est écrit (§5) et se prononce sur une liste, pas sur un sentiment. Le prononcé de ce seuil est une décision datée, à porter au registre à sa revue. |

## 6. Acceptations explicites

Un risque accepté et écrit est une décision ; le même risque non écrit est un oubli. Sont acceptés, en connaissance :

- **R-08** - le ré-encodage du corpus est un coût de travail, borné et sans arbitrage.
- **R-25** - qu'un autre comble l'écart de §1 est le but, pas la défaite.
- **R-02**, en résiduel - **D-07** confie à l'usager un jugement qu'il pourrait ne pas savoir exercer. C'est ce qui rend **D-01** et **D-03** tenables ensemble ; le refus explicite et l'élargissement en sont la contrepartie, non la garantie.
- **R-26**, en T0 - il n'existe pas de parade à l'acteur unique tant qu'il est unique. L'acceptation cesse au seuil de T1, où des tiers entrent.

## 7. Revue

**Le registre est repris à chaque tentative de validation d'un seuil de jalon.** Un seuil ne se prononce pas avant que la revue soit faite : c'est ce qui empêche le registre de devenir une pièce écrite une fois.

Trois déclencheurs, et pas de calendrier - aucune date ne structure ce projet (**C-07**) :

1. **À chaque tentative de validation d'un seuil** (T0 → T1 → T2). La revue reprend chaque ligne avec ce que la phase écoulée a appris : elle vérifie les hypothèses de §1, clôt ce qui est levé, réévalue les gravités, et **comble les manques** - ce premier jet vise l'exhaustivité sans l'atteindre.
2. **À l'ouverture d'une phase du plan en six.** Une phase qui s'ouvre rend décidable ce qui ne l'était pas : plusieurs réponses de §5 y renvoient explicitement.
3. **Quand un signal se lève.** La revue est alors partielle et porte sur le seul risque concerné.

**Ce que produit une revue** : des lignes closes, des lignes ajoutées, des gravités révisées, et le cas échéant une décision `D-xx` amendée dans la note de cadrage. Une revue qui ne change rien est un résultat à écrire comme tel.
