"""La table de rôles — **la source, réduite à une donnée**.

Ceci est la pièce qui décide si §3 tient : *« une source nouvelle = une table, pas un
second parser »*. Tout ce que ``sources/legi/parser.py`` savait de LEGI vivait dans
quatre constantes de module (``_CONTENT_BLOCKS``, ``_TITLE_TAGS``, ``_META_RENAMES``,
``_TRANSPARENT``) et dans deux ``frozenset`` de racines. Le code qui les *lisait*
(``_walk``, ``_find_all``, ``_text_blocks``) ne contenait, lui, pas un seul mot de LEGI.

Ce module extrait ces constantes du code et en fait un argument. Rien de plus — et c'est
tout le point : il n'y avait pas de parser LEGI à généraliser, il y avait un parser
générique qui portait ses tables en dur.

**Une table est inspectable.** On peut la lire, la comparer, la faire échouer sur une
balise inconnue, l'imprimer dans un bilan de run. Du code ne se laisse pas faire ça.
C'est le même argument que le catalogue d'events (§12) et que la table de traduction des
verbes : *la donnée déclarative bat le branchement conditionnel*.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from ragcore.core.links import LinkTable

from .roles import Role

__all__ = ["RoleTable"]


@dataclass(frozen=True)
class RoleTable:
    """Tout ce qu'une source déclare de sa structure XML. Une donnée, pas du code."""

    roots: frozenset[str]
    """Les racines XML que la source connaît (``ARTICLE``, ``TEXTE_JURI_JUDI``…).

    Une racine hors de cet ensemble ressort en ``unknowns["racine"]`` : c'est une famille
    de documents que la source n'a jamais déclarée, et le run doit le dire.
    """

    roles: Mapping[str, Role]
    """Le cœur : chaque balise, un rôle. **Un seul.**

    Une balise absente de cette table ressort en ``unknowns["balise"]``. Ce n'est pas un
    filtre de validation — c'est l'instrument : sur un corpus saturé, il ne déclare rien ;
    sur le prochain export, une balise neuve sort dans le bilan du run au lieu de
    disparaître.
    """

    content_blocks: Sequence[str] = ()
    """Les balises qui portent le TEXTE, dans l'ordre où on les lit.

    Distinct du rôle ``BODY`` : le rôle dit *ce qu'est* une balise, cette séquence dit
    *où chercher* et *dans quel ordre*. LEGI range son texte sous ``BLOC_TEXTUEL``, mais
    un ``TEXTE_VERSION`` n'en a pas (mesuré : 0/98) — le sien vit sous ``VISAS``,
    ``SIGNATAIRES``, ``TP``. Ne chercher qu'un seul bloc aurait ingéré les 98 décrets du
    corpus avec un contenu VIDE, sans qu'une exception soit levée.

    L'ordre compte : il fixe l'ordre du texte concaténé, donc les offsets des chunks.
    """

    text_holders: Sequence[str] = ()
    """Les balises qui, à l'intérieur d'un bloc de contenu, portent réellement le texte.

    ``<BLOC_TEXTUEL>`` enveloppe son texte dans ``<CONTENU>`` ; ``<VISAS>`` le porte
    directement. On descend s'il y a un porteur, sinon on lit le bloc lui-même.
    """

    title_tags: Sequence[str] = ()
    """Où chaque famille range son titre, **par ordre de préférence**.

    L'ordre est la règle de résolution des conflits à la fusion de facettes :
    ``TEXTE_VERSION`` apporte ``<TITRE>``, ``TEXTELR`` n'apporte rien (0/98) — c'est
    exactement pourquoi les deux doivent être lues ensemble, et pourquoi ``TITRE``
    l'emporte.
    """

    identifier_tag: str = "ID"
    """La balise qui porte l'identifiant du document.

    **Il n'existe aucune balise ``<ELI>`` dans le corpus LEGI** — vérifié : zéro
    occurrence sur 2564 fichiers. Le nom du modèle est historique ; la donnée est un ID.
    """

    meta_containers: Sequence[str] = ()
    """Les balises sous lesquelles chercher les métadonnées (``<META>``).

    Y restreindre la collecte évite d'aspirer en métadonnée le texte du corps ou les
    attributs des liens : ils ont leur place, et la dupliquer ferait deux vérités.
    """

    meta_renames: Mapping[str, str] = field(default_factory=dict)
    """Balise brute → nom du champ dans le domaine (``NATURE`` → ``type_document``).

    C'est le 4ᵉ axe non-standard : la **canonicalisation par type**. Une balise absente
    de ce renommage n'est pas perdue — elle atterrit en métadonnée sous son nom brut
    aplati. Le renommage est une promotion, pas un péage.
    """

    version_tags: frozenset[str] = frozenset()
    """Les balises de l'axe temporel (``DATE_DEBUT``, ``DATE_FIN``, ``ETAT``).

    **Vide en jurisprudence, et c'est prévu** (§3 : « version = stratégie optionnelle,
    no-op si absente »). Le handler ne s'active que si des balises de datation sont
    présentes. Le rôle existe toujours ; c'est la table qui décide s'il a du travail.
    """

    transparent: Mapping[str, str] = field(default_factory=dict)
    """Les balises de mise en forme : balise → séparateur inséré dans le texte.

    Elles portent du texte mais aucune sémantique. Leur contenu remonte dans le parent,
    et elles n'apparaissent pas dans la structure. **Ne pas les traverser ferait
    disparaître le texte qu'elles enveloppent** — c'est le cas de tout le corps des
    articles LEGI, entièrement contenu dans des ``<p>``.
    """

    links: LinkTable | None = None
    """Ce que la source déclare de ses liens — délégué à ``core/links`` (§7).

    Le parser **appelle** ``core/links``, il ne réimplémente jamais la mécanique des
    arêtes. C'est la frontière que la doctrine pose nommément, et que
    ``sources/legi/relations.py`` violait en portant sa propre notion d'orientation.
    """

    link_tags: Sequence[str] = ()
    """Les balises qui portent un lien déclaré (``<LIEN>``)."""

    link_containers: Sequence[str] = ()
    """Les conteneurs où chercher les liens STRUCTURELS (``<STRUCTURE_TA>``, ``<STRUCT>``).

    **Et jamais ailleurs.** Sous ``<VERSIONS>``, un ``LIEN_ART`` désigne les autres
    versions temporelles du MÊME article : ce n'est pas une contenance. Les émettre
    créerait des cycles et de faux parents. Restreindre la recherche à ces conteneurs
    n'est pas une optimisation — c'est ce qui rend le graphe correct.
    """

    structural_link_tags: Sequence[str] = ()
    """Les balises de lien structurel à chercher DANS les conteneurs ci-dessus."""

    ancestor_containers: Sequence[str] = ()
    """Les balises qui déclarent les ancêtres du document (``<CONTEXTE>``)."""

    ancestor_tags: Sequence[str] = ()
    """Les balises d'ancêtre à chercher dans ces conteneurs (``TITRE_TXT``, ``TITRE_TM``)."""

    ancestor_id_attrs: Sequence[str] = ("id_txt", "id")
    """Les attributs où lire l'identifiant d'un ancêtre, **par ordre de préférence**."""

    def role_of(self, tag: str) -> Role | None:
        """Le rôle d'une balise, ou ``None`` si la table ne la connaît pas.

        ``None`` n'est pas une erreur : c'est le signal qui alimente ``unknowns``. Une
        balise inconnue est une *découverte*, et le corpus enseigne ainsi son vocabulaire.
        """
        return self.roles.get(tag)

    def knows(self, tag: str) -> bool:
        """Vrai si la table sait ranger cette balise — sous un rôle, ou comme mise en forme.

        La mise en forme n'a pas de rôle (elle n'est *rien* dans le domaine, elle est
        traversée), mais elle est bel et bien connue. La confondre avec l'inconnu ferait
        remonter ``<p>`` et ``<br>`` dans le bilan de chaque run.
        """
        return tag in self.roles or tag in self.transparent or tag in self.roots
