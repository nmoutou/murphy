# Cartographie des parties prenantes - Murphy

## 1. Les acteurs

### 1.1 Ce dont le projet dépend pour exister

| N° | Acteur | Ce qu'il fournit |
|---|---|---|
| **PP-01** | **DILA** - Direction de l'information légale et administrative | Le corpus lui-même : textes consolidés et plusieurs bases jurisprudentielles, en diffusion ouverte. |
| **PP-02** | **Juridictions productrices** - Cour de cassation, Conseil d'État, Conseil constitutionnel | Les décisions, par leurs propres canaux. Chacune décide seule de ce qu'elle publie et à quel rythme. |
| **PP-03** | **Fournisseur du modèle de représentation** (poids ouverts) | Le modèle d'embedding. Dépendance réelle mais substituable : le coût d'un changement est un ré-encodage. |
| **PP-04** | **Hébergeur / infrastructure de calcul** | La disponibilité du service. Inexistant en tant qu'acteur tant que le service tourne en local. |

### 1.2 Ce qui autorise ou interdit

| N° | Acteur | Sur quoi il agit |
|---|---|---|
| **PP-05** | **Ordre des avocats - CNB** | Le monopole du conseil et de la qualification juridique. |
| **PP-06** | **CNIL** | 1. Les données personnelles **présentes dans le corpus** (jurisprudence). 2. Les données **des usagers**. |
| **PP-07** | **Autorité de surveillance IA** (AI Act) | La qualification du système. La question de classification est ouverte et transverse à toutes les phases. |

### 1.3 Ce qui complique la réussite du projet

| N° | Acteur | Enjeu |
|---|---|---|
| **PP-08** | **Éditeurs juridiques établis** | La couche éditoriale payante, et c'est l'écart qu'elle laisse que Murphy vise. Un usager qui atteint la source sans passer par eux est un abonnement en moins. |
| **PP-09** | **Legaltechs de recherche juridique** | Position ambiguë : même geste, modèle inverse. Concurrents sur la fonction, pas sur le public. |

### 1.4 Ce qui donne accès aux usagers

| N° | Acteur | Enjeu |
|---|---|---|
| **PP-10** | **Structures relais d'accès au droit** - conseils départementaux de l'accès au droit, maisons de justice et du droit, associations, cliniques juridiques universitaires, permanences syndicales | Elles tiennent l'accès physique à une grande partie du groupe B, et à plusieurs profils du groupe A. **Sans elles, le plan (b) de D-02 n'est pas mesurable** : on ne peut pas observer une tâche de recherche réelle sur des usagers qu'on n'atteint pas. |
| **PP-11** | **Juristes annotateurs** | Les jugements de pertinence qu'exige la phase 3. Rôle **inexistant** à ce jour. Recrutés dans le groupe A, ils y entrent comme acteurs et non comme demande. |
| **PP-12** | **Usagers du pilote** | La tâche réelle de D-02 (b). Rôle inexistant, ouvert en T1. |

### 1.5 Ceux qui font le travail

| N° | Acteur | Enjeu |
|---|---|---|
| **PP-13** | **Le porteur** | Conçoit, décide, exécute, et répond du tout. Seul acteur en position d'arbitrage. |
| **PP-14** | **Structure d'accueil ou financeur** | **N'existe pas.** Inscrit ici parce que son absence est une propriété du projet, pas un oubli : elle explique pourquoi le RACI est ajourné. |

---

## 2. Qualification

| N° | Enjeu pour l'acteur | Pouvoir T0 | Pouvoir T1 | Pouvoir T2 |
|---|---|---|---|---|
| **PP-01** DILA | Aucun. Le projet est un usager parmi d'autres de sa diffusion ouverte. | ⬛ | ⬛ | ⬛ |
| **PP-02** Juridictions | Aucun, hors volume d'appels. | ⬛ | ⬛ | ⬛ |
| **PP-03** Modèle de représentation | Aucun. | ⬛ | ⬛ | ⬛ |
| **PP-04** Hébergeur | Un client. |  | 🟦 | 🟦 |
| **PP-05** Ordre des avocats | L'exercice du conseil. Un service qui qualifierait des situations empiéterait. |  | ⬛ | ⬛ |
| **PP-06** CNIL | La protection des personnes, des deux côtés du système. |  | ⬛ | ⬛ |
| **PP-07** Surveillance IA | La conformité du système à sa catégorie. | ⬛ | ⬛ | ⬛ |
| **PP-08** Éditeurs | Un revenu, sur la part du public qui peut encore payer. |  |  | 🟧 |
| **PP-09** Legaltechs | Une position sur un marché voisin. |  |  | 🟧 |
| **PP-10** Structures relais | Un outil pour un public qu'elles servent déjà, gratuitement. Intérêt objectif **convergent**. |  | 🟧🟦 | 🟧🟦 |
| **PP-11** Annotateurs | Un travail spécialisé, rémunéré ou non - la question n'est pas tranchée. | ⬛ | ⬛🟦 | ⬛🟦 |
| **PP-12** Usagers du pilote | Une tâche qui les engage réellement. |  | 🟦 | 🟦 |
| **PP-13** Porteur | Le projet entier. | ⬛🟦 | ⬛🟦 | ⬛🟦 |
| **PP-14** Structure / financeur | Sans objet. |  |  | 🟦 |

#### Légende : 
- **⬛ structurel** : impacte directement le cadrage du projet
- **🟦 pratique** : impacte les activités du projet
- **🟧 indéterminé** : impact encore à définir
- **Case vide** : pas d'impact
