# Méthode — comment on avance et comment on se trompe

> Le découpage du droit est un problème pour lequel il n'existe pas de test
> qui dirait « c'est le bon ». On ne peut donc pas valider avant d'avoir
> utilisé. Ce document décrit ce qu'on peut **quand même** tester, et le
> moteur qui fait avancer le modèle sans le figer.

## 0. Régime de travail

**Les hypothèses de travail sont autorisées et attendues.** On avance par
tâtonnement, on itère sur ce qui est sûr et sur ce qui doit nécessairement
être représenté. La validation vient à la fin, pas à chaque pas.

La contrepartie : toute hypothèse s'écrit **comme hypothèse**, avec le test
qui la falsifierait. Une hypothèse sans test de falsification est une opinion
qu'on finira par défendre.

## 1. Les trois tests — sur une dimension candidate

| Test | Question | Si échec |
|---|---|---|
| **Nécessité** | Existe-t-il une question de droit qu'on ne peut pas poser correctement sans cette dimension ? | Écarter |
| **Constatabilité** | Deux juristes lisant la même source lui donneraient-ils la même valeur ? | Écarter, **ou** assumer un jugement et écrire sa règle |
| **Traçabilité** | D'où vient-elle ? Un énoncé du socle, un texte, ou une convention posée ? | Écarter |

Deux critères supplémentaires portent sur l'ensemble des facettes et non sur
une seule — indépendance et énumérabilité, énoncés en `FACETTES.md` §5.

## 2. Le moteur — la question orpheline

**Protocole.** Prendre une vraie question de droit. Tenter de la placer dans le
modèle courant. Ce qui ne se place pas est une dimension candidate, ou un
objet d'une nature non prévue.

C'est le seul générateur d'axes qu'on s'autorise en plus de la déduction depuis
le socle — et il est empirique sans être contingent : il ne demande rien aux
nomenclatures, seulement à des questions réelles.

**Règle de sélection des questions.** Elles doivent différer par leur *forme*,
pas par leur matière. Trois questions de droit du travail ne testent qu'un
point du modèle ; une question de forme inédite en teste la structure.

## 3. Journal des orphelines

| # | Question | Ce qui s'est placé | Ce qui a manqué |
|---|---|---|---|
| **O-01** | *« Mon employeur peut-il me licencier pendant mon arrêt maladie ? »* | F1, F2 (salarié/employeur), F4, modalité (interdiction) | **La source applicable dépend d'une norme non étatique** — convention de branche, accord d'entreprise — qui déroge à la loi si elle est plus favorable. Ni facette, ni rang simple : un **ordre conditionnel**. → `RELATIONS.md` R-a |
| **O-02** | *« Quel est le délai pour contester un permis de construire ? »* | F1, F3, F4, F5 (procédure) | **La qualité pour agir.** Ce n'est pas F2 : « voisin » n'est pas une qualité juridique tant qu'un intérêt à agir n'est pas caractérisé. C'est une **condition**, qui transforme un rôle de fait en rôle de droit. → `RELATIONS.md` R-b |
| **O-03** | *« Mon voisin a coupé une branche de mon arbre »* | F3, et le fait | **Rien du côté norme.** L'utilisateur ne connaît aucune qualification. Le modèle doit permettre d'entrer par le fait seul et de ressortir avec **plusieurs qualifications concurrentes** — art. 673 C. civ., trouble anormal de voisinage, dégradation pénale. → asymétrie norme/fait, `FACETTES.md` §6 |

**Bilan de la première passe** : trois questions, trois trouvailles, dont
**deux sont des conditions et non des dimensions**. C'est le signal le plus
fort obtenu jusqu'ici, et il n'était pas anticipé.

## 4. Ce qu'on pourra tester quand il y aura de la matière

Tests différés, listés pour ne pas être réinventés :

| Test | Énoncé | Automatisable |
|---|---|---|
| **Couverture** | Tout code LEGI en vigueur s'attache à au moins un concept de F1 ; le résidu est chiffré et nommé | Oui |
| **Pureté de facette** | Aucun concept ne mêle deux facettes — le test qu'échoue le PCJA avec `06 Alsace-Moselle` | Par revue |
| **Indépendance** | Information mutuelle entre facettes, sous un seuil à fixer | Oui, dès qu'il y a des données |
| **Divergence enregistrée** | Là où deux sources s'opposent sur un alignement, le désaccord est écrit, jamais arbitré en silence | Oui |
| **Non-vacuité** | Un concept sans aucune norme rattachée est soit une erreur, soit une lacune du corpus — jamais laissé indéterminé | Oui |

## 5. Ce qui n'est pas une méthode de validation

À écarter explicitement, parce que ce sont les tentations naturelles :

- **L'accord avec une nomenclature existante.** Elles qualifient des documents
  (C6) et portent chacune la marque d'un usage de gestion. Coïncider avec
  l'une d'elles ne prouve rien ; en diverger ne prouve rien non plus.
- **L'accord avec un découpage antérieur du projet.** Aucune continuité n'est
  recherchée avec les travaux d'évaluation. Ce modèle repart de zéro.
- **L'élégance.** Un modèle qui range tout sans reste est très probablement un
  modèle qu'on n'a pas encore éprouvé sur une question de forme inédite.
