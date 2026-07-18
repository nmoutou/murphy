# INSTITUTIONNEL — Cadrage du volet institutionnel (chantier 8)

> Document de cadrage **interne** préparant les livrables à audience **externe**
> (financeurs, administrations, futurs membres). Détaille le jalon « Création
> association » de `PROGRAM.md` §3 et alimente en retour les critères d'entrée
> des versions **beta** et **publication** (chantier 3).
>
> **Convention de lecture** : ✅ = tranché · 🔶 = proposition à valider ·
> ⬜ = ouvert (deviendra un ADR). Aucune date.

---

## 0. Objet et positionnement

- Horizon : **publication à l'échelle nationale** d'un service subventionné,
  porté par une **structure associative**, positionné « **commun numérique** ». ✅
- Ce document ne modifie pas le programme technique (versions par capacités
  mesurables) : il y injecte des **exigences externes** comme critères d'entrée.
- Déclencheur opérationnel : jalon « association » (entre beta et publication).
  Le cadrage, lui, démarre dès maintenant.

### 0.1 Audiences visées

| Audience | Livrable externe dérivé | Statut |
|----------|------------------------|--------|
| Financeurs (appels à communs, fondations, publics) | Dossier de présentation (§4) | ⬜ |
| Administrations / DILA | Diagramme de contexte + argumentaire conformité | ⬜ |
| Futurs membres / contributeurs | Statuts + gouvernance (§1) | ⬜ |

---

## 1. Structure juridique

### 1.1 Forme et statuts
- 🔶 Association loi 1901. Alternatives à documenter dans l'ADR : fonds de
  dotation, SCIC.
- ⬜ **ADR-INST-01** — Forme juridique de la structure porteuse.
- ⬜ Rédaction des statuts : objet social, membres, instances.

### 1.2 Gouvernance
- ⬜ Modèle de gouvernance (solo fondateur → collégiale ?) et trajectoire.
- ⬜ Place des experts alpha dans la gouvernance (contributeurs de golden-sets).

### 1.3 Propriété intellectuelle
Inventaire des actifs et régime par actif :

| Actif | Régime proposé | Statut |
|-------|----------------|--------|
| Code (P1, P2, P3) | ⬜ **ADR-INST-02** — licence du code | ⬜ |
| Données dérivées (chunks, embeddings, graphe) | 🔶 Licence Ouverte Etalab 2.0 (cohérence sources DILA) | 🔶 |
| Golden-sets (qrels expertes) | 🔶 Etalab 2.0 ; question de l'attribution des annotateurs | ⬜ |
| Marque « Murphy » | ⬜ dépôt INPI ? | ⬜ |

### 1.4 Positionnement « commun numérique »
- ⬜ Critères revendiqués (gouvernance ouverte, licences libres, réutilisabilité)
  et preuves associées — alimente le dossier de présentation (§4).

---

## 2. Modèle économique

### 2.1 Coûts d'exploitation
- ⬜ Chiffrage par poste : GPU/TEI, hébergement (bases + applicatif), LLM
  (si maintenu hors chemin de réponse), maintenance, refresh corpus DILA.
- ⬜ Deux scénarios : charge alpha (experts) vs charge publication (nationale).

### 2.2 Plan de financement
- ⬜ Cartographie des guichets : appels à communs (ANCT, ADEME num.), fondations,
  financements publics du numérique d'intérêt général, mécénat de compétences.
- ⬜ Calendrier conditionnel : quels guichets exigent quelle maturité
  (beta démontrée ? association créée ?).

### 2.3 Soutenabilité hors subvention
- ⬜ Pistes : services payants B2B (accès API ?), adhésions, dons — compatibilité
  avec le positionnement commun numérique à vérifier.
- ⬜ **ADR-INST-03** — Modèle de soutenabilité cible.

---

## 3. Conformité réglementaire

> Détail complet → §3.4 « Mapping conformité » (livrable 3, à produire).
> Principe : chaque exigence devient un **critère d'entrée** beta ou publication.

### 3.1 RGPD
- Contraintes déjà actées (héritées de `archive/BETA.md`) : E2EE des
  conversations, aucune analyse de contenu, métriques sans texte utilisateur. ✅
- ⬜ Registre des traitements.
- ⬜ AIPD (données sensibles saisies par les usagers → probablement requise).
- ⬜ Statut des données de jurisprudence (pseudonymisation amont DILA : vérifier
  le périmètre résiduel de responsabilité).

### 3.2 RGAA (accessibilité)
- Exigée pour un service à vocation nationale et par la plupart des financeurs
  publics. ✅
- ⬜ Niveau visé et périmètre (frontend P3) ; audit → critère d'entrée publication.

### 3.3 RGESN (écoconception)
- ⬜ Périmètre d'application (GPU d'embedding = poste principal) ; déclaration
  d'écoconception → critère d'entrée publication.

### 3.4 Mapping conformité → critères d'entrée ⬜
*(Livrable 3 — tableau exigence → référentiel → version d'entrée → preuve.)*

---

## 4. Dossier de présentation

### 4.1 Argumentaire d'impact
- ⬜ Problème (accès au droit), solution (sourcer sans raisonner), différenciation
  (exhaustivité DILA, évaluation mesurable, commun numérique).

### 4.2 Diagramme de contexte (C4 niveau 1) ⬜
*(Livrable 4 — Murphy dans l'écosystème DILA / usagers / financeurs.)*

### 4.3 KPIs d'impact ⬜
*(Livrable 2 — cadre à quatre niveaux : programme / produit-IR / service
opérationnel (ISO/IEC 25010) / impact externe. Les métriques IR internes
restent du ressort de P2 ; seuls les niveaux service et impact sont exposés
aux financeurs.)*

---

## 5. Interfaces avec le reste du programme

| De → Vers | Contrat |
|-----------|---------|
| INSTITUTIONNEL → `VERSIONS.md` | Exigences RGPD/RGAA/RGESN et KPIs = critères d'entrée beta / publication |
| INSTITUTIONNEL → `decisions/` | ADR-INST-01/02/03 versés au registre |
| P2 → INSTITUTIONNEL | Métriques IR alimentant les KPIs niveau produit (agrégées, jamais exposées brutes) |
| P3 → INSTITUTIONNEL | Métriques d'usage sans contenu → KPIs service et impact |
| `PROGRAM.md` §3 → ici | Référence au jalon « association » |

---

## 6. Décisions ouvertes (→ ADR)

- ⬜ **ADR-INST-01** — Forme juridique (association 1901 / fonds de dotation / SCIC).
- ⬜ **ADR-INST-02** — Licence du code.
- ⬜ **ADR-INST-03** — Modèle de soutenabilité hors subvention.
- ⬜ Régime des golden-sets (licence + attribution des annotateurs).
- ⬜ Niveau RGAA visé et périmètre d'audit.

---

## 7. Definition of Done — chantier 8

- [x] Squelette validé (ce document).
- [ ] Cadre de KPIs à quatre niveaux rédigé (§4.3).
- [ ] Mapping conformité → critères d'entrée rédigé (§3.4).
- [ ] C4 niveau 1 produit (§4.2).
- [ ] ADR-INST-01/02/03 tranchés et versés dans `decisions/`.
- [x] `PROGRAM.md` référence ce document (fait lors du chantier 7).
