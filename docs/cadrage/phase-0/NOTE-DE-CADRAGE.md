# Note de cadrage - Murphy

## 0. Décisions

| N° | Décision | 
|---|---|
| **D-01** | Est cible quiconque a besoin d'une source juridique française. Personne n'est écarté par avance |
| **D-02** | La valeur se mesure sur **deux plans de rang égal** : la qualité de la récupération et la substituabilité au contrefactuel. |
| **D-03** | Murphy **restitue des sources et n'interprète pas**. | 
| **D-04** | La génération de texte est interdite et destinée au retrait. |
| **D-05** | Le périmètre est fixé **par fonctionnalité, capacité, ou par source**, pas par matière. |
| **D-06** | Le service est **sans état d'usager** : ni historique, ni profil, ni personnalisation. Aucun résultat ne dépend de qui demande. Le sans-état porte sur **l'implémentation de la recherche**, non sur l'exploitation du service : il n'interdit pas les journaux de sécurité et de conformité (**D-08**, **D-10**). Ce qui est conservé l'est au strict nécessaire. |
| **D-07** | L'utilisateur **contrôle et dirige** sa recherche : il en est l'**opérateur**, non le destinataire d'un résultat. |
| **D-08** | **Rien de ce qui est conservé hors de l'IAM n'est joint à une identité**, à la seule exception des **journaux de sécurité et de conformité** : pseudonymisés, réduits aux métadonnées, joignables à une identité sur **fondement légal** seulement. L'exception est **énumérée** — ce qui n'y figure pas relève de la règle. |
| **D-09** | **L'anonymisation a lieu à l'entrée du système**, avant tout autre traitement. Aucun composant en aval ne reçoit jamais autre chose que des données anonymisées ou pseudonymisées. Le module est *fail-closed* : une anonymisation qui échoue produit une erreur, et rien n'est conservé. |
| **D-10** | **Aucun journal ne porte le contenu d'un échange** : ni requête, ni réponse, ni extrait de source restituée. Un journal enregistre qu'un événement a eu lieu, jamais ce qu'il disait. |
---

## 1. Le problème

**Le droit français est intégralement public et pratiquement inaccessible à qui ne sait pas par où commencer.**

Le droit est publié, gratuit et complet. L'accès formel est un problème résolu depuis longtemps. Ce qui ne l'est pas, c'est l'accès effectif : **le moteur public exige le vocabulaire de la réponse comme clé d'accès à la réponse.** On y cherche par référence ou par mots du texte. Qui sait déjà comment la règle se nomme la trouve en quelques secondes ; qui ne le sait pas ne la trouve pas du tout, et n'a aucun moyen de distinguer "cette règle n'existe pas" de "je n'ai pas su la nommer".

La couche qui comble cet écart existe : plans de classement, mots-clés, notes, jurisprudence rattachée. Elle est éditoriale, privée et payante. Elle n'est pas illégitime : elle est simplement hors de portée d'une partie de ceux qui en ont besoin, et c'est précisément cette partie-là qui n'a pas d'alternative.

---

## 2. Les utilisateurs cibles

> **D-01 - Est cible quiconque a besoin d'une source juridique française. Personne n'est écarté par avance.**

Une question permet de distinguer deux groupes : **le droit est-il l'objet direct de l'activité ?** S'il est, groupe **A**, groupe **B**, s'il ne l'est pas. 

### Groupe A

| Utilisateur | Rapport à la source |
|---|---|
| **Avocat en cabinet individuel ou de petite structure** | Lit le texte et l'arrêt pour en tirer une conduite ; toutes matières, tous les jours. La source fonde le conseil, puis l'écriture. |
| **Juriste unique en entreprise** | Lit couramment, mais sur des matières qui débordent sa spécialité ; le texte arrête une décision avant qu'elle soit prise. |
| **Juriste d'association, de permanence d'accès au droit** | Un socle étroit - droit social, séjour, aide sociale - mobilisé en volume, sur des dossiers courts. |
| **Défenseur syndical** | Cite pour opposer ; code du travail et convention collective sont l'autorité qu'il produit face à une partie outillée. |
| **Juriste de collectivité territoriale** | Fonde des actes relus par un tiers - commande publique, urbanisme, fonction publique ; le texte doit tenir devant le contrôle de légalité. |
| **Agent public instructeur** | Applique le même corps de textes à des dossiers en série ; le texte est une règle de décision, pas un objet d'étude. |
| **Étudiant en droit** | Apprend à lire le texte et à en dériver un raisonnement ; en acquiert le vocabulaire, ne l'a pas encore. |
| **Doctorant en droit** | Prend le texte pour objet : exhaustivité, versions successives, état du droit à une date. |
| **Enseignant en droit** | Expose la source plus qu'il ne l'applique ; doit pouvoir la montrer entière et exacte. |
| **Expert-comptable** | Applique le texte fiscal en routine ; en connaît la matière, rarement la référence. |
| **Gestionnaire de paie** | Articule deux étages de norme - code du travail et convention de branche ; jamais un texte isolé. |
| **Conseil en gestion de patrimoine** | Le texte décide d'un montage - fiscalité, régimes matrimoniaux, successions - et il répond de la lecture qu'il en fait. |
| **Juriste abonné, en vérification** | Atteint le texte par sa couche éditoriale ; ne revient à la source brute que pour confirmer. |

### Groupe B

| Utilisateur | Rapport à la source |
|---|---|
| **Justiciable en litige** | Le texte le concerne sans qu'il sache le nommer ; la règle de fond ne lui dit pas la procédure. |
| **Salarié sur ses propres droits** | Part des faits - « mon employeur a… » - et n'a pas les mots du texte qui les régit. |
| **Locataire** | Attend du texte une réponse fermée et courte : congé, charges, dépôt de garantie. |
| **Bailleur particulier** | Doit connaître l'obligation avant de l'enfreindre ; le texte est une contrainte à respecter, pas un argument à opposer. |
| **Consommateur** | Demande au texte l'existence d'un droit avant d'en demander l'exercice. |
| **Dirigeant de TPE** | Rencontre le droit à chaque décision engageante - embaucher, rompre, contracter - puis le quitte. |
| **Travailleur indépendant, artisan** | Statut, cotisations, obligations déclaratives ; ne lit le texte qu'après l'incident qu'il aurait prévenu. |
| **Responsable associatif bénévole** | Statuts, obligations déclaratives, responsabilité des dirigeants : des textes qui l'obligent et qu'il n'a jamais lus. |
| **Travailleur social** | Connaît le dispositif, pas le texte qui le fonde ; en manie le vocabulaire administratif, jamais les références. |
| **Aidant familial** | Vient au texte par un événement - protection d'un majeur, aide sociale, succession - jamais par une question de droit. |
| **Élu local** | Le texte fait preuve en séance ; il lui en faut la lettre, pas une lecture. |
| **Journaliste** | Cite le texte sans l'appliquer ; l'exactitude de la citation est l'enjeu, pas la conséquence juridique. |
| **Chercheur non juriste** | Sociologue, économiste, historien : le texte est un matériau, voulu en série et daté. |

---

## 3. La valeur

**Murphy restitue des documents publics, des sources, et rien d'autre.** Aucune réponse rédigée, aucun résumé, aucune synthèse : le système ne restitue pas un mot de texte qui ne soit déjà dans le corpus. Ce que l'usager formule en langue naturelle n'est donc pas seulement une question dont il attendrait la réponse, mais aussi une **équation de recherche**. La requête permet de constituer un ensemble de documents, puis de l'élargir, de le concentrer ou de le déplacer.

**Murphy est un service de recherche documentaire, pas de questions-réponses.** L'usager n'est pas seulement le destinataire du résultat, il est **opérateur et garant** de sa propre recherche. C'est ce qui rend D-01 tenable, puisqu'on suppose que l'utilisateur sait (et, en fait, doit) juger, seul, si un document le concerne. L'ensemble d'un résultat ne s'évalue pas en "juste" et "faux" mais en **"bruit"** et **"silence"** - un couple qui ne couvre pas tout : une réponse **bien formée et fausse**, la version en vigueur restituée quand une version passée était demandée, n'est ni l'un ni l'autre, et aucun signal ne la distingue d'une bonne réponse. L'unité de valeur n'est pas seulement l'ensemble *restitué* mais surtout l'ensemble **atteignable** : lequel, et en combien de gestes.

> **D-07 - L'utilisateur contrôle et dirige sa recherche : il en est l'opérateur, non le destinataire d'un résultat.**

**Le sans-état est la forme propre de l'objet.** Une seconde requête est une nouvelle équation de recherche, **neuve** ; Chaque tour doit porter son contexte, en entier. Une équation de recherche se juge sur ce qu'elle demande, jamais sur qui la pose.  

### Mesures de la valeur

La sortie de Murphy n'est rien d'autre que l'ensemble récupéré, la qualité de la récupération **est** la qualité du produit.

Une collection de test doit confronter le système à des jugements de pertinence. La collection ne permet pas de dire ce qu'un usager aurait fait sans Murphy, sur une tâche qui l'engage. Cette valeur ne se mesure pas contre un idéal mais contre un **scénario contrefactuel** : ce que la cible fait aujourd'hui, faute de mieux.

> **D-02 - La valeur se mesure sur deux plans de rang égal.**
> **(a) La qualité de la récupération**, sur collection de test. Mesurable dès qu'une collection existe.
> **(b) La substituabilité au contrefactuel**, sur une tâche de recherche réelle : **taux de tâches abouties** et **temps jusqu'à la première source pertinente**.

**L'ordre d'arrivée des capacités n'est pas une hiérarchie.** La valeur (a) se mesure d'abord parce qu'elle est constructible en premier, non pas parce qu'elle compte davantage.

---

## 4. Périmètre

### Dedans

| Dedans | Borne | Motif |
|---|---|---|
| La récupération de sources juridiques françaises publiées, **toutes matières** (**D-05**) | Fonctionnalité | Le problème posé en §1. |
| **L'identité canonique et vérifiable** de chaque source, portée par les identifiants du producteur | Capacité | Un identifiant interne serait invérifiable hors du système ; sans identité opposable, l'usager ne peut pas exercer le jugement que **D-07** lui confie. |
| **Le refus explicite** : ne rien restituer plutôt que du bruit | Capacité | Tient le plancher de non-fabrication. Tenable seulement parce que l'élargissement existe (§3) : sans geste correctif, un refus est une impasse. Vaut aussi pour le refus d'anonymisation (**D-09**), qui doit donc dire quoi reformuler. |
| **La déclaration de ce qui manque** : le système dit ce qu'il **n'a pas trouvé**, et ce qu'il **ne peut pas trouver** | Capacité | Contrepartie du refus explicite, et non son doublon : celui-ci porte sur ce que Murphy ne fait pas, celle-là sur ce qu'il n'a pas. Sans elle, un ensemble vide se lit *« la règle n'existe pas »* — l'impasse de §1 reproduite à l'intérieur du produit (**R-48**), et le contrôle humain de l'art. 14 reste une intention (**R-20**). Les deux énoncés ne se remplacent pas : le premier porte sur la requête servie et suppose une identité à vérifier, le second sur l'état du corpus et vaut avant toute requête — c'est lui qui couvre ce que le premier n'atteint pas. Exigible **dès T0**, où il ne coûte presque rien : l'art. 13 (**R-42**) et l'art. 15 (**R-21**) imposent déjà d'en déclarer la substance. Sa contrepartie est **R-57** — un système qui dit ce qu'il n'a pas peut le dire à tort. |
| **L'invariance du résultat à l'usager** (**D-06**) : à corpus et configuration donnés, la même requête rend le même ensemble, quel que soit le demandeur | Capacité | Chaque équation est neuve (§3). La personnalisation supposerait d'observer l'usager, quand le seul jugement utile est le sien sur la source. C'est aussi la condition de **D-02(a)** : une collection de test ne mesure rien si le résultat dépend de qui interroge. Il suit qu'**aucun classement ne s'apprend de l'usage** — un tel classement renforcerait les chemins déjà empruntés, donc servirait le mieux ceux qui savaient déjà chercher (§1). |
| **L'injointabilité** (**D-08**) : aucune donnée conservée hors de l'IAM ne porte d'identifiant de compte, et aucune jointure vers l'IAM n'existe — ni en base, ni en code | Capacité | Fait de la minimisation une propriété d'architecture plutôt qu'une promesse (§5) : elle se lit dans un schéma, se cherche en revue de code, s'oppose en AIPD. |
| **La journalisation de sécurité et de conformité** (**D-08**, **D-10**), seule exception à l'injointabilité : pseudonymisée, réduite aux métadonnées, joignable à une identité sur fondement légal | Capacité | Le régime haut-risque impose d'enregistrer les événements et de les conserver ; ce que l'injointabilité interdisait partout devient obligatoire ici. L'exception est donc **énumérée et close** — c'est ce qui la distingue d'un renoncement. Ce qu'elle ne couvre pas reste sous la règle. |
| **L'absence de contenu dans les journaux** (**D-10**) : un journal enregistre qu'un événement a eu lieu, jamais ce qu'il disait | Capacité | Plancher qui rend l'exception ci-dessus tenable : une trace joignable à une identité n'est acceptable que si elle ne dit rien de ce qui a été cherché ni de ce qui a été lu. Sans ce plancher, l'exception rouvre exactement ce que **D-06** ferme. |
| **L'anonymisation à l'entrée** (**D-09**) : le contenu des requêtes est anonymisé avant tout autre traitement ; l'échec produit une erreur et rien n'est conservé | Capacité | Supprime le besoin de faire confiance aux composants en aval : aucun ne peut divulguer ce qu'il n'a jamais reçu. Le corpus étant du droit général et non des dossiers, ce qui identifie une personne n'a pas de valeur de récupération. |

**Le périmètre n'est pas l'état du corpus.** Ce qui est dedans l'est par sa nature de source - toute source juridique française publiée par son producteur - et non par le fait d'avoir déjà été ingéré. Une base publiée que l'ingestion n'a pas encore reprise n'est pas dehors : elle est en attente, et le manque se déclare à l'usager plutôt qu'il ne le découvre. La distinction opère dans les deux sens : elle interdit qu'une capacité s'active parce qu'elle est là (**R-45**), et symétriquement qu'un périmètre se rétrécisse en silence jusqu'à ce qui se trouve chargé - **R-37** posant déjà, pour la base perdue, qu'elle doit être *un périmètre en moins, jamais un service arrêté*.

**Bornes d'exécution.** La clé de session est tirée au hasard, jamais dérivée du compte, de l'IP ou d'une empreinte d'appareil, et n'est pas réutilisée d'une session à l'autre. **Hors des journaux de sécurité et de conformité, le couple compte↔clé de session n'est jamais écrit** : partout ailleurs, il n'existe qu'en mémoire, le temps de l'échange. Une seule trace de ce couple **en dehors du périmètre énuméré** — table de sessions, cache, trace de débogage, sauvegarde — rendrait nominatif, par une seule jointure, tout ce qui est en aval.

Le périmètre énuméré obéit à trois bornes. **Il est clos** : la liste des journaux concernés, et pour chacun la liste des champs, est écrite et ne s'étend que par décision. **Il est muet sur le fond** : aucun champ ne porte de contenu d'échange (**D-10**), ce qui vaut aussi pour les traces de débogage, les messages d'erreur et les sauvegardes. **Il est borné dans le temps** : chaque journal a une durée de conservation déclarée, au moins celle qu'exige le régime haut-risque, au terme de laquelle il est supprimé — une conservation sans terme n'est pas une conformité, c'est un gisement.

### Dehors

| Dehors | Borne | Motif |
|---|---|---|
| **L'interprétation, la qualification, le conseil** (**D-03**) | Fonctionnalité | L'écart d'interprétation n'est pas le problème traité (§1), et aucun dispositif ne mesure la justesse d'une interprétation. |
| **La rédaction d'actes** et tout livrable textuel destiné à être produit tel quel | Fonctionnalité | Un texte produit tel quel n'est pas une source. |
| **La génération de texte comme fonction pérenne** (**D-04**) | Fonctionnalité | Le conseil et la qualification juridique sont monopolisés par l'ordre des avocats. |
| **Le droit non publié par le producteur** : doctrine, droit étranger, sources privées | Source | Trop ambiteux pour la v1. |
| **L'affinage du modèle de représentation** sur le corpus, **jusqu'à T2 au moins** | Capacité | Murphy n'entraîne rien : le modèle est pris sur étagère. Ce n'est pas un détail d'implémentation, c'est ce qui maintient un régime. Tant que rien n'est entraîné, l'art. 10 de l'AI Act ne s'applique qu'aux jeux de **test** ; dès qu'un modèle est affiné, il s'applique **en entier**, entraînement et validation compris. Cette capacité ne rentre donc pas dans le périmètre parce qu'elle serait devenue accessible ou peu coûteuse (**D-05**) : elle rentre au vu de la charge de conformité qu'elle déclenche, ou elle ne rentre pas. |

---

## 5. Principaux jalons

**Trois régimes se succèdent, séparés par ce qui peut atteindre le système.** Les jalons ne sont pas définis par des dates.

| Phase | Ce qui la définit | Seuil de sortie |
|---|---|---|
| **T0** | Le système n'a qu'un utilisateur, son auteur. Rien n'est atteignable de l'extérieur. Aucune donnée personnelle de tiers n'existe. | Le service est **presque publiable** et ce qui l'en sépare est surtout : de l'argent, une personnalité juridique, et des tiers. AIPD obligatoire. |
| **T1** | Des utilisateurs invités, sur un système hébergé. L'accès est restreint, nominatif et révocable. | L'appareil de conformité a été **exercé** et non plus seulement écrit. La structure qui portera le service existe et est financée. La CNIL a été notifiée. |
| **T2** | L'accès est ouvert. | Aucun. Ce qui suit la publication n'est pas encore nommé. |

### T0 - La construction

Un critère unique trie ce qui relève de T0 : **le service serait-il publiable si publier était gratuit et ne demandait aucune structure ?** Tout ce qu'un travail solitaire et sans argent peut produire doit être produit ici. 

**Ce socle doit être autant juridique que technique**

Le cadrage en est le premier segment. T0 porte la **quasi-totalité de l'architecture définitive** : elle est construite pour les deux régimes, d'évaluation et opérationnel, alors que seul le premier tournera en T1 ; Le régime opérationnel n'y est pas disponible. On y construit déjà ce qui sert à observer et à exploiter le système. Rattraper une architecture au moment où les utilisateurs arrivent est précisément ce que T1 ne peut pas et ne doit pas faire.

Toutefois, certaines pièces ne peuvent-être **exercées** seulement en T1 : demandes d'accès réellement traitées, durées de conservation réellement appliquées, violations réellement notifiées. 

Rien de tout cela ne passe devant un guichet, toutefois, c'est la phase où l'on s'y prépare ; "Montrer patte blanche", c'est **pouvoir produire le dossier sur demande**, à tout moment.

**La minimisation des risques PII est et doit rester une propriété d'architecture, même initialement.**

Il en résulte une liste **close et courte** des données personnelles de T1 : les identifiants d'accès, les retours du régime d'évaluation et les journaux techniques de sécurité. 

### T1 - L'exposition restreinte

Plusieurs itérations, avec deux profils d'utilisateurs différents : les groupes A et B définis en §2.

**T1 n'élargit pas le périmètre fonctionnel.** La totalité du travail de developpement est : d'amélioration, de mise en conformité, de correction et/ou d'optimisation de ce qui existe déjà.

**Le versionnement des briques est une condition d'entrée.** Toutes les observations viennent désormais d'un système déployé, et **plusieurs choses y varient à la fois** : corpus, configuration d'ingestion, graphe, runtime, jugements de référence, utilisateurs. Une notation, un retour ou une mesure qu'on ne peut pas rattacher à l'état exact qui l'a produite est une donnée perdue en silence. Chaque artefact déployé doit être identifiable au même titre que ce qui l'a fabriqué.

Enfin, **T1 est la phase où la structure porteuse est montée** : statut, financements, conseils. La conformité, elle, n'y est pas construite mais **éprouvée** : T0 en a constitué l'appareil, T1 est le premier régime où des tiers l'exercent réellement. Ces conditions sont toutes bloquantes pour l'ouverture de T2.

### T2 - L'accès ouvert

Rien ne s'y décide aujourd'hui. Ce que T2 contient se tranchera au seuil de sortie de T1, avec ce que T1 aura mesuré : en décider maintenant serait décider sans ce qu'il faut savoir. 

Au-delà, aucun jalon n'est fixé, et les noms de cette section n'y survivront pas ; Ce qui suit la publication demande une précision que rien ne fonde encore.
