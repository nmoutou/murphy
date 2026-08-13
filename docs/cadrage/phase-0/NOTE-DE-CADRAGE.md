# Note de cadrage — Murphy

*Phase 0 — cadrage stratégique. Ce document ne cite rien : ce qu'il retient, il le décide.*

---

## 0. Décisions

| N° | Décision | 
|---|---|
| **D-01** | Est cible quiconque a besoin d'une source juridique française. Personne n'est écarté par avance |
| **D-02** | La valeur se mesure sur **deux plans de rang égal** : la qualité de la récupération et la substituabilité au contrefactuel. |
| **D-03** | Murphy **restitue des sources et n'interprète pas**. | 
| **D-04** | La génération de texte borderline interdite et est destiné au retrait. |
| **D-05** | Le périmètre est fixé **par fonctionnalité, capacité, performance, ou par source**, jamais par matière. |
| **D-06** | Le service est **sans état** : ni historique, ni profil, ni personnalisation. |
| **D-07** | L'utilisateur **contrôle et dirige** sa recherche : il en est l'**opérateur**, non le destinataire d'un résultat. |
---

## 1. Le problème

**Le droit français est intégralement public et pratiquement inaccessible à qui ne sait pas par où commencer.**

Le droit est publié, gratuit et complet. L'accès formel est un problème résolu depuis longtemps. Ce qui ne l'est pas, c'est l'accès effectif : **le moteur public exige le vocabulaire de la réponse comme clé d'accès à la réponse.** On y cherche par référence ou par mots du texte. Qui sait déjà comment la règle se nomme la trouve en quelques secondes ; qui ne le sait pas ne la trouve pas du tout, et n'a aucun moyen de distinguer « cette règle n'existe pas » de « je n'ai pas su la nommer ».

La couche qui comble cet écart — plans de classement, mots-clés, notes, jurisprudence rattachée — existe. Elle est éditoriale, privée et payante. Elle n'est pas illégitime : elle est simplement hors de portée d'une partie de ceux qui en ont besoin, et c'est précisément cette partie-là qui n'a pas d'alternative.

---

## 2. Les utilisateurs cibles

> **D-01 — Est cible quiconque a besoin d'une source juridique française. Personne n'est écarté par avance.**

Une question permet de distinguer deux groupes : **le droit est-il l'objet direct de l'activité ?**. S'il est, groupe **A**, groupe **B**, s'il ne l'est pas. 

### Groupe A  

| Utilisateur | Rapport à la source |
|---|---|
| **Avocat en cabinet individuel ou de petite structure** | Lit le texte et l'arrêt pour en tirer une conduite ; toutes matières, tous les jours. La source fonde le conseil, puis l'écriture. |
| **Juriste unique en entreprise** | Lit couramment, mais sur des matières qui débordent sa spécialité ; le texte arrête une décision avant qu'elle soit prise. |
| **Juriste d'association, de permanence d'accès au droit** | Un socle étroit — droit social, séjour, aide sociale — mobilisé en volume, sur des dossiers courts. |
| **Défenseur syndical** | Cite pour opposer ; code du travail et convention collective sont l'autorité qu'il produit face à une partie outillée. |
| **Juriste de collectivité territoriale** | Fonde des actes relus par un tiers — commande publique, urbanisme, fonction publique ; le texte doit tenir devant le contrôle de légalité. |
| **Agent public instructeur** | Applique le même corps de textes à des dossiers en série ; le texte est une règle de décision, pas un objet d'étude. |
| **Étudiant en droit** | Apprend à lire le texte et à en dériver un raisonnement ; en acquiert le vocabulaire, ne l'a pas encore. |
| **Doctorant en droit** | Prend le texte pour objet : exhaustivité, versions successives, état du droit à une date. |
| **Enseignant en droit** | Expose la source plus qu'il ne l'applique ; doit pouvoir la montrer entière et exacte. |
| **Expert-comptable** | Applique le texte fiscal en routine ; en connaît la matière, rarement la référence. |
| **Gestionnaire de paie** | Articule deux étages de norme — code du travail et convention de branche ; jamais un texte isolé. |
| **Conseil en gestion de patrimoine** | Le texte décide d'un montage — fiscalité, régimes matrimoniaux, successions — et il répond de la lecture qu'il en fait. |
| **Juriste abonné, en vérification** | Atteint le texte par sa couche éditoriale ; ne revient à la source brute que pour confirmer. |

### Groupe B 

| Utilisateur | Rapport à la source |
|---|---|
| **Justiciable en litige** | Le texte le concerne sans qu'il sache le nommer ; la règle de fond ne lui dit pas la procédure. |
| **Salarié sur ses propres droits** | Part des faits — « mon employeur a… » — et n'a pas les mots du texte qui les régit. |
| **Locataire** | Attend du texte une réponse fermée et courte : congé, charges, dépôt de garantie. |
| **Bailleur particulier** | Doit connaître l'obligation avant de l'enfreindre ; le texte est une contrainte à respecter, pas un argument à opposer. |
| **Consommateur** | Demande au texte l'existence d'un droit avant d'en demander l'exercice. |
| **Dirigeant de TPE** | Rencontre le droit à chaque décision engageante — embaucher, rompre, contracter — puis le quitte. |
| **Travailleur indépendant, artisan** | Statut, cotisations, obligations déclaratives ; ne lit le texte qu'après l'incident qu'il aurait prévenu. |
| **Responsable associatif bénévole** | Statuts, obligations déclaratives, responsabilité des dirigeants : des textes qui l'obligent et qu'il n'a jamais lus. |
| **Travailleur social** | Connaît le dispositif, pas le texte qui le fonde ; en manie le vocabulaire administratif, jamais les références. |
| **Aidant familial** | Vient au texte par un événement — protection d'un majeur, aide sociale, succession — jamais par une question de droit. |
| **Élu local** | Le texte fait preuve en séance ; il lui en faut la lettre, pas une lecture. |
| **Journaliste** | Cite le texte sans l'appliquer ; l'exactitude de la citation est l'enjeu, pas la conséquence juridique. |
| **Chercheur non juriste** | Sociologue, économiste, historien : le texte est un matériau, voulu en série et daté. |

---

## 3. La valeur

### Ce que Murphy restitue

**Des documents publics, des sources, et rien d'autre.** Aucune réponse rédigée, aucun résumé, aucune synthèse : le système ne restitue pas un mot de texte qui ne soit déjà dans le corpus. Ce que l'usager formule en langue naturelle n'est donc pas seulement une question dont il attendrait la réponse, mais aussi une **équation de recherche** : elle constitue un ensemble de documents, puis l'élargit, le concentre ou le déplace.

### Le cadre : recherche documentaire, non question-réponse

**Le déplacement n'est pas de vocabulaire : il fixe trois choses, et toute la suite en dépend.** L'usager n'est pas seulement le destinataire d'un résultat, il est **opérateur et garant** de sa recherche — c'est ce qui rend D-01 tenable, puisqu'on ne suppose pas qu'il connaisse le vocabulaire du droit, seulement qu'il sache — et, en fait, qu'il doive — juger seul si un document le concerne. Les modes d'échec ne sont plus « juste » et « faux » mais **bruit** et **silence**, deux défauts opposés appelant deux gestes opposés. Et l'unité de valeur n'est pas seulement l'ensemble *restitué* mais surtout l'ensemble **atteignable** : lequel, et en combien de gestes.

> **D-07 — L'utilisateur contrôle et dirige sa recherche : il en est l'opérateur, non le destinataire d'un résultat.**
> *Écarté : le système qui devine l'intention et livre l'ensemble juste du premier coup. Quand il se trompe, l'usager n'a aucun geste — il ne peut ni voir ce qui a été écarté, ni le récupérer, ni même savoir qu'un écart a eu lieu.*

**Le sans-état est la forme propre de l'objet.** La seconde équation est une équation **neuve** : l'usager la réécrit avec ce qu'il a appris de l'ensemble précédent, il ne poursuit pas une conversation. Chaque tour porte donc son équation entière — D-06 n'est pas une privation qu'on s'impose.

> Note, à déplacer : Les états sont autorisés, seulement aux conditions suivantes :
> - temporairement seulement
> - toujours sauvegardés du côté client, JAMAIS du côté serveur
> - anonymisé en régime opérationnel, et pseudonymisé en régime d'évaluation

**Le détail est différé.** Quels gestes de pilotage, sur quoi ils portent, ce qu'ils garantissent : c'est le premier objet du **cahier des charges fonctionnel**, livrable de phase 1. Cette note en pose le cadre, pas le contenu.

### Deux mesures, de rang égal

**La récupération a changé de statut.** Tant que Murphy produisait une réponse, elle mesurait un **composant** — un étage du pipeline, pas le produit. Quand la sortie n'est rien d'autre que l'ensemble récupéré, la qualité de la récupération **est** la qualité du produit ; elle cesse d'être une mesure interne.

**Elle ne devient pas pour autant la mesure de la valeur.** L'écart demeure, mais déplacé : il ne sépare plus le composant du produit, il sépare **le jugement fabriqué du besoin réel**. Une collection de test confronte le système à des jugements de pertinence que le programme produit lui-même ; elle ne dit rien de ce qu'un usager, sur une tâche qui l'engage, aurait fait sans Murphy. Ce second plan ne se mesure pas contre un idéal mais contre un **scénario contrefactuel** — ce que la cible fait aujourd'hui, faute de mieux : pour le cœur de cible, le moteur public ou un modèle généraliste, jamais la base éditoriale payante, à laquelle elle n'a pas accès.

> **D-02 — La valeur se mesure sur deux plans de rang égal.**
> **(a) La qualité de la récupération**, sur collection de test. Mesurable dès qu'une collection existe.
> **(b) La substituabilité au contrefactuel**, sur une tâche de recherche réelle : **taux de tâches abouties** et **temps jusqu'à la première source pertinente**, en comparaison appariée — même tâche, deux outils. Mesurable seulement quand des utilisateurs existent.
>
> *Écarté : subordonner l'un des deux plans à l'autre.* Faire de (a) un indicateur avancé de (b) rendrait invérifiable tout gain que (b) ne confirme pas, donc aveugle toute la phase de construction, puisque (b) n'est pas mesurable avant longtemps. Faire de (b) le contrôle de (a) reviendrait à donner tort à l'usager, le jour où il ne trouve rien alors que la métrique est excellente.

**L'ordre d'arrivée des capacités n'est pas une hiérarchie.** (a) se mesure d'abord parce qu'elle est constructible d'abord, non parce qu'elle compte davantage : le « pour l'instant » qualifie le calendrier de l'instrument, jamais le rang de la mesure.

**Règle opératoire.** Une version doit **déplacer au moins un des deux plans sans dégrader l'autre**. C'est ce que consomme la règle de découpe (§9) : un jalon se ferme sur l'un des deux plans, jamais sur un lot livré.

*Écarté : la couverture du corpus comme valeur. C'est une entrée, pas un résultat.*

### Ce que la mesure doit sanctionner en priorité

**Sanctionner d'abord le défaut qu'un geste ne répare pas** — un ordre de priorité qu'un choix de métrique standard ne donnerait pas. Un silence que l'usager lève en élargissant coûte un tour ; un bruit qu'il ne peut pas distinguer d'une source pertinente coûte la confiance, et aucun geste ne le rattrape. C'est aussi ce qui rend le refus explicite (§4) défendable : préférer le silence au bruit n'est tenable **que parce que l'élargissement existe**. Sans geste correctif, un refus n'est pas une prudence — c'est une impasse.

### Ce qu'aucune des deux mesures ne porte

**La trajectoire.** Une collection de test mesure **un tour** — postulat de sa construction, non défaut d'exécution, et aucun raffinement ne le comble ; la substituabilité mesure **une tâche, aboutie ou non**. Entre les deux, la suite de gestes par laquelle l'ensemble converge n'est mesurée par personne, or c'est précisément là que D-07 place la valeur.

L'écart est porté en hypothèse **H-07** ; son instrumentation relève de la phase 3, une fois le pilotage spécifié en phase 1. D'où l'intérêt de trancher D-02 et D-07 maintenant plutôt que le jour où ils seront mesurables : une définition de la valeur écrite après coup se règle sur ce qu'on sait déjà mesurer.

---

## 4. Périmètre

**Dedans.**

- La récupération de sources juridiques françaises publiées, **toutes matières** (**D-05**). *Écarté : le découpage thématique — il se défend par la profondeur éditoriale, terrain perdu d'avance ici, et rend le refus inqualifiable : hors sujet, ou lacune ?*
- **L'identité canonique et vérifiable** de chaque source, portée par les identifiants du producteur. *Écarté : un identifiant interne, invérifiable hors du système.*
- **Le refus explicite** : ne rien restituer plutôt que du bruit — c'est ce qui tient le plancher de non-fabrication.
- **Un service sans état** : ni historique, ni profil, ni personnalisation (**D-06**). *Écarté : la personnalisation — elle suppose d'observer l'usager, quand le seul jugement utile est celui de l'utilisateur sur la source.*

**Dehors.**

- **L'interprétation, la qualification, le conseil** (**D-03**) : l'écart d'interprétation n'est pas le problème traité (§1), et aucun dispositif ne mesure la justesse d'une interprétation.
- **La rédaction d'actes** et tout livrable textuel destiné à être produit tel quel.
- **La génération de texte comme fonction pérenne** (**D-04**) : présente aujourd'hui, elle est un échafaudage ; son retrait est un objectif, pas une régression.
- **Le droit non publié par le producteur retenu** — doctrine, droit étranger, sources privées. *Exclusion par source, vérifiable, et non par matière, qui ne l'est pas.*

---

## 5. Hypothèses

*Tenues pour vraies, susceptibles d'être fausses. Chacune porte la décision qui tombe avec elle.*

| N° | Hypothèse | Si fausse |
|---|---|---|
| **H-01** | Il existe un volume significatif de besoins juridiques où **une source suffit pour agir** — propriété du besoin, non de qui le porte. | D-02 n'a pas de tâche à mesurer, et ce qui manquerait est précisément ce que §4 met dehors. Le cadrage entier tombe. |
| **H-02** | Le cœur de cible n'a pas accès à la couche éditoriale payante, et cet accès ne se démocratise pas pendant la durée du programme. | Le contrefactuel du plan (b) de D-02 change ; la substituabilité s'évapore sans que la récupération ait démérité — les deux plans divergent sans faute du système. |
| **H-03** | Le dispositif de mesure du plan (b) sera constructible quand des utilisateurs existeront. | Le plan (b) de D-02 reste indisponible. La valeur ne se démontre plus que contre des jugements que le programme produit lui-même : le juge et partie (§7) devient structurel, sans contrepoids. |
| **H-04** | Les deux plans de D-02 sont corrélés : ce qui progresse sur collection de test progresse sur tâche réelle. | Les deux plans peuvent diverger, et rien ne dit lequel suivre. Leur arbitrage redevient un jugement, alors que D-02 le voulait mesuré. |
| **H-05** | Le producteur public continue de publier ces corpus sous une licence permettant l'usage projeté. | Le périmètre de §4 se réduit aux sources qui restent, sans recours. |
| **H-06** | La non-fabrication est atteignable **par construction**, l'identité étant portée par le corpus et non produite par le système. | La non-fabrication cesse d'être un plancher binaire et redevient un objectif de qualité gradué — donc négociable. |
| **H-07** | La **trajectoire** — la suite de gestes par laquelle l'ensemble converge — sera instrumentable une fois le pilotage spécifié (phase 1) et l'évaluation conçue (phase 3). | La valeur que D-07 place dans le pilotage reste hors mesure : on saura noter un tour et constater une tâche aboutie, jamais ce qui mène de l'un à l'autre. Le pilotage devient une promesse invérifiable. |

---

## 6. Contraintes

*Subies, non décidées. Chacune porte ce qu'elle interdit.*

| N° | Contrainte | Interdit |
|---|---|---|
| **C-01** | Un seul contributeur. | Tout dispositif supposant une équipe : revue croisée native, annotation collective, continuité en cas d'absence. |
| **C-02** | Aucun financement. | L'achat de jugements ; l'accès aux bases payantes à fin de comparaison ; l'infrastructure louée en continu. |
| **C-03** | Le calcul dépend d'une machine locale. | Traiter la disponibilité comme acquise ; toute promesse de continuité de service. |
| **C-04** | Le corpus est celui que le producteur publie, dans la forme où il le publie. | Supposer une métadonnée absente ; corriger la source. |
| **C-05** | Aucun utilisateur réel à ce jour. | Toute mesure du plan (b) de D-02 aujourd'hui ; toute segmentation validée par l'observation. |

---

## 7. Risques majeurs

Le registre complet est tenu séparément → `REGISTRE-DES-RISQUES.md`. Quatre risques commandent ce cadrage :

- **La disparition du contributeur unique** (C-01) — le seul risque dont la réalisation arrête tout, et le seul contre lequel la documentation est la parade.
- **Le juge et partie** — celui qui construit le système construit aussi le jeu qui l'évalue. Le risque n'est pas la malhonnêteté, c'est l'angle mort partagé entre les deux ouvrages.
- **L'absence de mesure de valeur** (H-03) — un programme qui mesure son instrument avec précision et sa valeur pas du tout.
- **L'outillage de pilotage** — le temps consacré à documenter la construction cesse à un moment d'être investi dans la construction, et rien ne signale le franchissement.

---

## 8. Gouvernance

> **La décision est solitaire et assumée ; la contradiction est instrumentée.**

Il n'y a qu'un décideur. Le risque n'est donc ni la lenteur ni le conflit — c'est **l'absence de contradicteur**. La gouvernance consiste ici à fabriquer de la contradiction en l'absence d'opposant :

- toute décision est écrite avec l'alternative qu'elle écarte et le motif de l'écart — c'est le régime de cette note, et il vaut au-delà d'elle ;
- tout instrument de mesure est conçu pour pouvoir **infirmer**, jamais seulement pour confirmer ;
- toute hypothèse porte sa condition de chute (§5), ce qui la rend réfutable par quelqu'un d'autre que son auteur.

La cartographie des parties prenantes et la répartition des rôles sont tenues séparément → `PARTIES-PRENANTES.md`. Un point s'y anticipe : le producteur des données est une partie prenante **subie**, non consultée — on ne négocie ni son format, ni son calendrier, ni sa licence.

---

## 9. Jalons — la règle de découpe

Cette section n'arrête ni la liste des jalons ni leurs dates : c'est une décision de pilotage. Elle fixe ce qui **fait** un jalon.

> **Un jalon est fermé par une mesure, pas par un lot de fonctionnalités.**

Dérivé de §3 : si la valeur est une mesure, un jalon qui se ferme sur un périmètre livré ne dit rien de l'avancement vers la valeur — il dit seulement qu'on a travaillé.

Tout jalon énonce donc **à l'avance** : (a) la mesure qui le ferme ; (b) le seuil ; (c) ce qu'on fait si le seuil n'est pas atteint. **Un jalon sans (c) n'est pas un jalon** — c'est une date, et une date se déplace.

**La logique de versions qui en découle.** Une version est un **palier de capacité mesurable**, non un lot. Leur ordre n'est pas commandé par la difficulté de construction mais par les **dépendances de mesure** : on ne mesure pas la substituabilité (**D-02**, plan b) avant qu'un tiers puisse se servir du système ; on ne mesure pas la qualité de récupération avant de disposer d'une collection de test ; on ne construit pas de collection de test avant que le corpus soit figé et identifié.

**Corpus → instrument → système → valeur.** C'est un ordre de mesure, pas un ordre de développement, et c'est lui qui découpe les versions. Une version qui ne déplace aucune de ces quatre mesures n'est pas une version.
