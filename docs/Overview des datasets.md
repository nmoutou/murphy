# Overview des datasets

---

Le site de la Direction de l’Information Légale et Administrative (DILA) met à disposition l’ensemble des données légales.

https://www.dila.premier-ministre.gouv.fr/services/repertoire-des-informations-publiques/les-donnees-juridiques

Le lien ci-dessus ramène sur une page de présentation des différents jeux de données légales librement accessibles en ligne.

---

Chaque jeu de données sera décrit séparément, avant de pouvoir donner de la cohérence à l’ensemble des jeux de données en décrivant leurs relations. 

Les données sont mises à dispositions au format **XML**, soit à travers un API, soit en téléchargement direct. 

Je privilégierai le téléchargement direct, puis j’explorerai, nettoierai et préparerai chaque jeu de données tout en documentant le processus.

| **Nom** | **Description** | Fiche de présentation |
| --- | --- | --- |
| LEGI | Codes, lois et règlements consolidés | https://echanges.dila.gouv.fr/OPENDATA/LEGI/DILA_LEGI_Presentation_20170824.pdf |
| JORF | Textes publiés au Journal Officiel de la République Française | https://echanges.dila.gouv.fr/OPENDATA/JORF/DILA_JORF_Presentation_20170824.pdf |
| DOLE | Dossiers législatifs | https://echanges.dila.gouv.fr/OPENDATA/DOLE/DILA_DOLE_Presentation_20181018.pdf |
| Assemblée nationale : Comptes rendus | Comptes rendus des débats de l’Assemblée nationale | https://echanges.dila.gouv.fr/OPENDATA/Debats/AN/DILA_Debats_Assemblee_nationale_20190611.pdf |
| Assemblée nationale : Questions réponses | Questions / Réponses de l’Assemblée nationale | https://echanges.dila.gouv.fr/OPENDATA/Questions-Reponses/AN/DILA_Debats-Assemblee_nationale_Questions-R%c3%a9ponses_20190611.pdf |
| KALI | Conventions collectives nationales | https://echanges.dila.gouv.fr/OPENDATA/KALI/DILA_KALI_Presentation_20170824.pdf |
| CASS | Arrêts publiés de la Cour de cassation | https://echanges.dila.gouv.fr/OPENDATA/CASS/DILA_CASS_Presentation_20170824.pdf |
| INCA | Arrêts inédits de la Cour de cassation | https://echanges.dila.gouv.fr/OPENDATA/INCA/DILA_INCA_Presentation_20170824.pdf |
| CAPP | Décisions des cours d’appel et des juridictions judiciaires de 1er degré | https://echanges.dila.gouv.fr/OPENDATA/CAPP/DILA_CAPP_Presentation_20170824.pdf |
| CONSTIT | Décisions du Conseil constitutionnel | https://echanges.dila.gouv.fr/OPENDATA/CONSTIT/DILA_CONSTIT_Presentation_20170824.pdf |
| JADE | Décisions des juridictions administratives | https://echanges.dila.gouv.fr/OPENDATA/JADE/%20DILA_JADE_Presentation_20171212.pdf |
| CNIL | Délibérations de la CNIL | https://echanges.dila.gouv.fr/OPENDATA/CNIL/DILA_CNIL_Presentation_20170824.pdf |
| CIRCULAIRES | Instructions et circulaires des ministères | https://echanges.dila.gouv.fr/OPENDATA/CIRCULAIRES/DILA_CIRCULAIRES_Presentation_20170828.pdf |
| SARDE | Référentiel thématique sur la majeure partie des textes législatifs et réglementaires en vigueur | https://echanges.dila.gouv.fr/OPENDATA/SARDE/DILA_SARDE_Presentation_20170830.pdf |
| Protocole du gouvernement | Constitution des gouvernements successifs depuis 2014 | https://echanges.dila.gouv.fr/OPENDATA/Protocole_du_Gouvernement/DILA_Protocole-Gouvernement_Presentation20170824.pdf |
| Protocole des JAAI | Liste des Juridictions, autres Autorités Administratives Indépendantes et établissements publics publiant au Journal officiel lois et décrets | https://echanges.dila.gouv.fr/OPENDATA/Protocole_des_JAAI/DILA_Protocole-JAAI_Presentation_20170824.pdf |

---

## Jurisprudence (décisions de justice)

La jurisprudence n’est pas un jeu de données unique : elle est répartie sur plusieurs jeux DILA distincts, selon l’ordre de juridiction. Pour obtenir **toute** la jurisprudence, il faut couvrir l’ensemble des datasets ci-dessous.

| **Dataset** | **Ordre / juridiction** | **Contenu** | **Téléchargement direct (XML)** |
| --- | --- | --- | --- |
| **CASS** | Judiciaire — Cour de cassation | Arrêts **publiés** | https://echanges.dila.gouv.fr/OPENDATA/CASS/ |
| **INCA** | Judiciaire — Cour de cassation | Arrêts **inédits** | https://echanges.dila.gouv.fr/OPENDATA/INCA/ |
| **CAPP** | Judiciaire — cours d’appel & 1er degré | Décisions des cours d’appel et juridictions judiciaires de 1er degré | https://echanges.dila.gouv.fr/OPENDATA/CAPP/ |
| **JADE** | Administratif | Décisions des juridictions administratives (Conseil d’État, CAA, TA) | https://echanges.dila.gouv.fr/OPENDATA/JADE/ |
| **CONSTIT** | Constitutionnel | Décisions du Conseil constitutionnel | https://echanges.dila.gouv.fr/OPENDATA/CONSTIT/ |

**Couverture :**

- **Ordre judiciaire** : CASS + INCA (Cour de cassation, arrêts publiés *et* inédits) + CAPP (appel et 1er degré).
- **Ordre administratif** : JADE.
- **Conseil constitutionnel** : CONSTIT.

Ces 5 jeux de données réunis constituent la jurisprudence DILA disponible en open data. Les autres jeux du tableau ci-dessus (LEGI, JORF, KALI, etc.) relèvent du droit positif ou des travaux parlementaires, et non de la jurisprudence.

**Où regarder :** racine `https://echanges.dila.gouv.fr/OPENDATA/`, puis le sous-dossier de chaque dataset (`/CASS/`, `/INCA/`, `/CAPP/`, `/JADE/`, `/CONSTIT/`). Chaque jeu propose un stock initial (archives complètes) et des incréments. Le schéma XML diffère de celui de LEGI : chaque dataset nécessite son propre parseur côté ingestion.

> **Note projet :** le pipeline d’ingestion actuel (`data/`) n’ingère que **LEGI** (textes consolidés). La jurisprudence est explicitement hors scope de la bêta (voir [BETA.md](BETA.md)).