# Coquilles — lot exécuté

> Fautes de frappe dans la documentation et dans les noms de fichiers.
> **Exécuté le 25 septembre 2026**, non commité. Index :
> [`README.md`](README.md).
>
> Méthode : `codespell` (anglais), puis `aspell` (dictionnaire français)
> sur les mots rares de tous les `.md`, `.ts`, `.tsx`, `.py` et `.yml`
> suivis. Les néologismes techniques volontaires (*requalification*,
> *renumérotation*, *fingerprinté*…) sont laissés tels quels.

## 1. Corrigé

| ID | Fichier | Avant | Après |
|---|---|---|---|
| CQ-01 | `docs/cadrage/phase-0/NOTE-DE-CADRAGE.md:149` | ne peuvent-être **exercées** seulement en T1 | ne peuvent être **exercées** qu'en T1 |
| CQ-02 | `docs/cadrage/phase-0/NOTE-DE-CADRAGE.md:161` | developpement | développement |
| CQ-03 | `docs/cadrage/phase-0/CARTOGRAPHIE-PARTIES-PRENANTES.md:68` | indeterminé | indéterminé |
| CQ-04 | `docs/cadrage/phase-1/TAXONOMIE-DES-REQUETES.md:7` | non-personalisation | non-personnalisation |
| CQ-05 | `docs/cadrage/phase-1/TAXONOMIE-DES-REQUETES.md:7` | en temps que propriété | en tant que propriété |
| CQ-06 | `docs/cadrage/phase-1/TAXONOMIE-DES-REQUETES.md:47` | L'axe prpopsé | L'axe proposé |
| CQ-07 | dossier `docs/droit/taxomonie/` | `taxomonie/` | `taxonomie/` : 8 fichiers déplacés, 7 références mises à jour |
| CQ-08 | `docs/pilotage/WIP/cadrage/` | `descripion-target-golden-set.md` | `description-target-golden-set.md` : 3 références mises à jour |
| CQ-09 | `docs/pilotage/WIP/cadrage/` | `descripion-current-golden-set copy.md` | `description-current-golden-set.md` : coquille corrigée et suffixe « copy » retiré (espace dans le nom) |

Les renommages sont faits avec `git mv` : ils sont donc **indexés**
(`git status` affiche `R`). Les corrections de texte ne sont pas indexées.

## 2. Laissé en l'état, volontairement

| Occurrence | Raison |
|---|---|
| « à priori » (`TAXONOMIE-DES-REQUETES.md:47`) | graphie admise par les rectifications orthographiques de 1990 |
| « dédupli-quées » (`ragcore/core/ports/parser.py:15`) | césure de fin de ligne dans une docstring, pas une coquille |
| « Suppresion » (`frontend/src/components/KeyComboListener.tsx:16`) | le fichier est du code mort voué à la suppression (FE-04) ; corriger le commentaire créerait un diff inutile dans le sous-module |
| identifiants sans accents (`ministere`, `autorite`, `cardinalite`, `polysemique`…) | noms de balises DILA, de champs ou de fichiers : ce sont des identifiants, pas de la prose |
