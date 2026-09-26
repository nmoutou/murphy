# ADR-025 — Environnement panel consenti pour métriques comportementales

> Clôt la décision ouverte ⬜ « architecture deux modes de P3 ».

**Statut** : 🔶 Proposé — 19 juillet 2026
**Version cible** : beta (aucun impact v0 / alpha ph.1)

## Contexte

L'invariant transverse actuel (« toutes les métriques KPI de niveaux 3–4
doivent être calculables sans contenu utilisateur ») interdit de fait
toute métrique online (CTR, dwell time, abandon, reformulation,
interleaving). Or ces signaux comportementaux sont trop importants pour
être ignorés : ils constituent la seule mesure de la qualité perçue en
usage réel, complémentaire des strates offline (ADR-017).

Par ailleurs, la structure existe déjà en germe : l'alpha (ADR-010,
interface P3→P2) fait précisément remonter requêtes réelles et
annotations depuis des experts consentants dans un environnement dédié.
La décision « architecture deux modes de P3 » était restée ouverte.

## Décision

Le programme opère **deux environnements de déploiement d'un même
artefact P3** :

| | Environnement **public** | Environnement **panel** |
|---|---|---|
| Accès | Ouvert | Beta-testeurs avec **opt-in explicite** |
| Collecte comportementale | **Aucune** | Télémétrie d'évaluation documentée |
| Config de récupération | Config de référence | **Identique** + configs candidates en interleaving |
| Base légale | — | Consentement (RGPD art. 6), finalité limitée à l'évaluation |

Contrat formel : `env_panel = env_public + télémétrie + configs
candidates`. **Même code, même config de référence, mêmes bases** — la
seule différence est une couche de télémétrie activée par flag (et
l'interleaving, qui n'existe que côté panel). Deux environnements, pas
deux branches : tout fork de code ou de config est proscrit, car il
détruirait la transférabilité des mesures du panel vers le public.

L'invariant transverse est **reformulé** (et non supprimé) :

> Par défaut, aucune donnée comportementale n'est collectée. Toute
> collecte comportementale vit dans l'environnement panel, sous opt-in
> explicite, à finalité d'évaluation documentée et publiée.

### Règles d'usage des mesures panel

1. **Comparaisons relatives uniquement** : le panel sert à des verdicts
   appariés (« config B > config A », interleaving team-draft, test
   apparié). Le biais de sélection du panel affecte A et B pareillement ;
   le verdict relatif y survit.
2. **Aucun chiffre absolu du panel n'est exposé** (en interne comme aux
   financeurs) : un CTR ou taux d'abandon mesuré sur un panel
   auto-sélectionné ne se généralise pas à la population.
3. **Interleaving privilégié sur l'A/B** : à petit trafic, seul
   l'interleaving (10–100× plus efficace en échantillon) a une puissance
   statistique utile. L'A/B classique est différé à un volume suffisant.

## Conséquences

**Positives**
- Débloque les métriques online sans compromettre l'environnement public,
  qui reste vierge de toute collecte — position renforcée, pas affaiblie,
  au sens RGPD (base légale claire, finalité limitée, minimisation).
- Pérennise la structure de l'alpha au lieu de la démonter en beta : le
  mode annotation (ADR-010) devient un cas particulier du mode panel.
- Argument institutionnel : un panel d'évaluation consenti et documenté
  (analogue panel Médiamétrie) est un gage de sérieux pour un commun
  numérique devant DINUM/ANCT.
- Les signaux comportementaux du panel deviennent une source
  supplémentaire de diagnostics/qrels aux côtés des strates ADR-017.

**Négatives / coûts**
- **AIPD** quasi certaine ; gestion du consentement, du retrait, de la
  durée de rétention ; publication de la liste des données collectées
  (→ `INSTITUTIONNEL.md`, chantier 8).
- Discipline d'ingénierie : le contrat « même artefact, flag de
  télémétrie » doit être vérifiable (test/CI comparant les configs
  déployées des deux environnements).
- Le panel ne remplace pas l'offline : les strates 1–4 restent le socle ;
  le panel n'est puissant que pour départager des configs, pas pour
  mesurer une qualité absolue.

## Impacts documentaires

| Document | Modification |
|---|---|
| `HANDBOOK.md` | Reformulation de l'invariant transverse (ci-dessus) |
| `PROGRAM.md` §2 | Clôture de la décision ouverte « deux modes P3 » ; interface P3→P2 étendue aux signaux comportementaux panel |
| `INSTITUTIONNEL.md` | Section consentement / AIPD / transparence de la collecte |
| ADR-017 | Ajout d'une ligne « signaux online panel » au tableau des strates (pérennité : liée au panel, comparaisons relatives uniquement) |
| `VERSIONS.md` (beta) | Critère d'entrée : environnements public/panel opérationnels, AIPD réalisée |

## Références

ADR-010 (modes annotation), ADR-016 (contrat d'adapter), ADR-017
(strates d'évaluation), décision ouverte « architecture deux modes P3 »,
`INSTITUTIONNEL.md` (RGPD/AIPD).
