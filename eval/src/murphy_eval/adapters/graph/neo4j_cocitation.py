"""``Neo4jCocitationMiner`` — le minage des paires de co-citation (lecture seule).

L'ingestion (``ragcore``) est *write-only* sur Neo4j ; le harnais définit son
propre chemin de lecture, exactement comme ``QdrantSearchClient`` pour Qdrant
(ADR-027, aucun import de ``ragcore``). Client **synchrone** à dessein : le sweep
d'ADR-027 est séquentiel (une ingestion, un graphe à la fois), rien à gagner à
l'asynchrone ici — même si l'écriture côté ingestion, elle, est asynchrone.

**Ce que la requête extrait, et ce qu'elle écarte.** Une paire = une arête directe
orientée ``(a)-[r]->(b)`` entre deux nœuds document. Le graphe (B-00/B-03) porte :

- des arêtes typées par le **verbe** de citation (``type(r)``), qu'on émet tel quel
  — B-07 est un socle neutre, tout jugement de pertinence des verbes est déporté
  sur B-09 (ADR-029) ;
- des nœuds ``:Pending`` : des cibles *identifiées mais dont le document n'est pas
  (encore) arrivé*. Une paire n'a de sens diagnostique que si les **deux** documents
  existent réellement (sinon B-09 ne pourra jamais les retrouver dans un run), donc
  on les exclut aux deux bouts — pendant graphe du fail-fast « collection
  incohérente » de la baseline.

Le ``owner_id`` est un **paramètre** de filtrage (invariant multi-tenant du graphe),
jamais une donnée de sortie : un jeu de paires est intégralement intra-tenant. Les
auto-arêtes (``a = b``) sont écartées : un document est trivialement lié à lui-même,
c'est un artefact sans valeur diagnostique.

Les cibles *décrites en français* (cf. ``ragcore`` : prop JSON ``citations`` du nœud
source, non des arêtes) ne remontent jamais dans ce ``MATCH`` — aucun filtrage
supplémentaire nécessaire de ce côté.
"""

from __future__ import annotations

from neo4j import GraphDatabase

from murphy_eval.core.models.cocitation import CocitationPair

_DOCUMENT_LABELS = ("Document", "Article", "Texte", "Section")
"""Les labels que l'ingestion pose sur un nœud **document** — recopiés, pas importés.

ADR-027 interdit à ``eval/`` d'importer ``ragcore`` : cette liste est donc un
**miroir délibéré** du contrat d'ingestion (ADR-018), et la duplication est le prix
de la frontière. L'ensemble est **fermé** : ``merge_document_node`` calcule le label
depuis ``identifier.document_type`` (``ARTI``/``TEXT``/``SCTA`` → ``Article``/
``Texte``/``Section``) et retombe sur ``Document`` pour tout le reste — décisions,
JORF, uploads n'ayant pas de ``document_type``, **toute la jurisprudence** est
étiquetée ``Document``.

Sans ce filtre, ``MATCH (a)-[r]->(b)`` n'exprimerait *aucune* hypothèse sur ce qu'est
un document : le jour où un ``:Chunk``, un ``:Run`` ou un nœud de télémétrie entrerait
dans le graphe, il rejoindrait le jeu de paires en silence et B-09 croirait
diagnostiquer une précision documentaire.

**Garde-fou de dérive** : ``tests/integration/test_neo4j_cocitation_real.py::
test_mine_pairs_filtre_pending_auto_autre_tenant_et_non_documents`` seede un nœud
hors contrat et exige son exclusion. Un label ajouté côté ``ragcore`` sans l'être ici
se verra là — c'est le fil à tirer.

**Réserve — cette exhaustivité est déduite, pas mesurée.** Elle vient de la lecture
de ``merge_document_node``, non de l'observation d'un corpus ingéré ; le test
d'intégration ne la prouve pas non plus, son seed portant par construction les labels
attendus. Un label documentaire non recensé ici ferait *disparaître des paires
légitimes en silence* — défaut inverse de celui que ce filtre corrige, et plus grave,
car sans erreur levée. Contrôle à faire dès que le minage est exécutable sur un vrai
graphe : compter les paires avec et sans ce filtre, les deux chiffres doivent être
**identiques** (consigné dans ``docs/pilotage/BACKLOG.md`` §2, note B-07).
"""

_LABEL_FILTER = " OR ".join(f"{{n}}:{label}" for label in _DOCUMENT_LABELS)
"""Le prédicat de label, dérivé de ``_DOCUMENT_LABELS`` — jamais réécrit à la main.

Gabarit à une variable (``{n}``) : ``.format(n="a")`` le lie à une extrémité. Le
dériver plutôt que le recopier est ce qui garantit que la constante et la requête ne
peuvent pas diverger. L'interpolation dans le Cypher est sûre — c'est une constante du
module, jamais une entrée utilisateur (les valeurs, elles, restent paramétrées)."""

_MINE_QUERY = f"""
MATCH (a)-[r]->(b)
WHERE a.owner_id = $owner_id AND b.owner_id = $owner_id
  AND ({_LABEL_FILTER.format(n="a")})
  AND ({_LABEL_FILTER.format(n="b")})
  AND NOT (a = b)
  AND NOT a:Pending AND NOT b:Pending
RETURN a.identifier AS source, type(r) AS verb, b.identifier AS target
ORDER BY source, verb, target
"""
"""Le tri ``ORDER BY`` fige l'ordre de sortie côté serveur : le fichier JSONL est
alors reproductible bit-à-bit sans re-trier en Python (mêmes octets à chaque run).

Les parenthèses autour de chaque ``OR`` de labels sont **nécessaires** : un ``OR`` nu
se lierait plus lâchement que les ``AND`` voisins et ouvrirait le filtre en grand.

**L'auto-arête s'exclut sur les nœuds (``NOT (a = b)``), pas sur leurs identifiants.**
La version ``a.identifier <> b.identifier`` avait un effet de bord mesuré contre un
vrai serveur : en Cypher, toute comparaison avec ``NULL`` vaut ``NULL`` — jamais
``TRUE`` — donc un nœud **sans** ``identifier`` faisait échouer le prédicat et
disparaissait de la requête *en silence*. Un nœud hors contrat était ainsi écarté au
lieu d'être signalé, ce qui vidait ``_record_to_pair`` de sa raison d'être. Comparer
les nœuds ne dépend d'aucune propriété : l'auto-arête reste exclue, et l'incohérence
remonte jusqu'au fail-fast.

``NOT a:Pending`` est **redondant** avec le filtre de labels (un ``:Pending`` non
ré-hydraté ne porte aucun label métier) et gardé quand même : les deux clauses disent
deux intentions distinctes — « c'est un document » et « ce document est réellement
arrivé » — et la redondance ne coûte rien."""


class Neo4jCocitationMiner:
    """Mine les paires de co-citation d'un tenant depuis le graphe (lecture seule).

    Utilisable comme **gestionnaire de contexte** — la forme à préférer :

        with Neo4jCocitationMiner(uri, auth=auth) as miner:
            pairs = miner.mine_pairs(owner_id="default")

    ``close()` reste public pour les appelants qui gèrent eux-mêmes la durée de vie
    de la connexion (le composeur CLI, qui doit fermer dans un ``finally`` couvrant
    aussi son propre code).
    """

    def __init__(self, uri: str, *, auth: tuple[str, str]) -> None:
        self._driver = GraphDatabase.driver(uri, auth=auth)

    def mine_pairs(self, *, owner_id: str) -> list[CocitationPair]:
        with self._driver.session() as session:
            result = session.run(_MINE_QUERY, owner_id=owner_id)
            return [_record_to_pair(record.data()) for record in result]

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> Neo4jCocitationMiner:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _record_to_pair(record: dict[str, object]) -> CocitationPair:
    """Traduit une ligne Cypher en ``CocitationPair``, fail-fast sur valeur nulle.

    Miroir de ``qdrant_search._point_to_hit`` : une ligne dont un champ manque trahit
    un graphe incohérent avec le contrat d'ingestion (ADR-018) — on échoue franchement
    plutôt que de fabriquer une paire silencieusement fausse.

    **C'est la nullité qu'on teste, pas la présence de la clé.** ``RETURN a.identifier
    AS source`` rend *toujours* les trois clés : une propriété absente vaut ``None``,
    jamais ``KeyError``. Un ``except KeyError`` ne se déclencherait donc jamais, et
    ``str(None)`` produirait l'identifiant ``"None"`` — précisément la paire fausse et
    silencieuse que ce garde-fou existe pour empêcher.
    """
    missing = [key for key in ("source", "verb", "target") if record.get(key) is None]
    if missing:
        raise ValueError(
            f"Ligne Neo4j sans {', '.join(missing)} — graphe incohérent avec le "
            f"contrat d'ingestion (identifier + type d'arête attendus)."
        )
    return CocitationPair(
        source=str(record["source"]),
        verb=str(record["verb"]),
        target=str(record["target"]),
    )
