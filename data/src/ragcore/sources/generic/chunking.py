"""Le chunker structurel — **générique**, et dont les offsets ne mentent plus.

**Il vivait dans ``sources/legi/`` et n'a pas changé d'une ligne en déménageant.** Ce
n'est pas une coïncidence, c'est un diagnostic : il ne connaissait déjà aucun mot de
LEGI. Il ne lit que ``document.content`` et ``document.structure["sections"]`` — le
contrat que *tout* parser générique honore. Six sources partageront donc un chunker,
sans qu'une ligne ait eu à être généralisée : il l'était.

**Il n'était pas cassé : il était inerte.** Sa découpe structurelle lisait
``document.structure["sections"]`` — un champ que le parser n'écrivait jamais. Elle
rendait donc toujours une liste vide, et le chunker retombait *systématiquement* sur le
découpage à taille fixe. La branche structurelle existait, elle n'a jamais tourné une
seule fois.

**Les offsets mentaient.** L'ancienne version faisait ``document.content.find(text)`` et
posait ``char_start = 0`` quand elle ne trouvait pas — ce qui arrivait dès que le texte
de la section n'était pas un morceau littéral du contenu. Un ``char_start`` faux ne lève
rien : il désigne simplement le mauvais passage, et personne ne s'en aperçoit.

Le parser garantit désormais l'invariant qui rend ce calcul honnête : **``_content`` et
``_sections`` lisent les mêmes blocs, dans le même ordre**, donc chaque section EST un
morceau littéral de ``content``. Le chunker peut chercher à partir du curseur précédent
plutôt qu'en repartant de zéro — ce qui, en prime, cesse de faire pointer deux sections
identiques au même endroit.
"""

from ragcore.core.models import Chunk, ParsedDocument

__all__ = ["StructuralChunker"]


class StructuralChunker:
    name = "structural"

    def __init__(self, max_chunk_size: int = 1000, overlap: int = 100) -> None:
        if overlap >= max_chunk_size:
            # Sinon le curseur du découpage à taille fixe n'avance pas : boucle infinie.
            raise ValueError(
                f"overlap ({overlap}) doit être strictement inférieur à "
                f"max_chunk_size ({max_chunk_size})"
            )
        self._max_chunk_size = max_chunk_size
        self._overlap = overlap

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        """Découpe le document : la structure dit OÙ couper, la taille dit JUSQU'OÙ aller.

        **Ce ne sont pas deux stratégies concurrentes.** L'ancienne version choisissait
        l'une *ou* l'autre — et donc, dès qu'un bloc structurel existait, elle le rendait
        entier. Sur le corpus, un article fait couramment 3000 caractères là où
        ``chunk_size`` en vaut 128 : l'embedder aurait tronqué en silence (la fenêtre
        d'``all-mpnet-base-v2`` est de 384 tokens), et les trois quarts du texte se
        seraient évaporés sans qu'aucune exception ne soit levée.

        La structure borne donc le découpage, elle ne le remplace pas : on ne coupe
        jamais À TRAVERS un bloc, et on ne dépasse jamais la taille dans un bloc.

        **Un document sans contenu ne rend AUCUN chunk.** Les 287 ``SECTION_TA`` du
        corpus n'ont pas de texte (mesuré : 0/287) : ce sont des nœuds de structure, pas
        des porteurs de contenu. Leur fabriquer un chunk vide reviendrait à embarquer du
        néant, puis à le proposer en réponse à un utilisateur.
        """
        if not document.content.strip():
            return []

        blocks = self._blocks(document)
        chunks: list[Chunk] = []
        ordinal = 0

        for path, text, offset in blocks:
            for start, end in _windows(len(text), self._max_chunk_size, self._overlap):
                chunks.append(
                    self._chunk(
                        document,
                        ordinal=ordinal,
                        text=text[start:end],
                        path=path,
                        char_start=offset + start,
                        char_end=offset + end,
                    )
                )
                ordinal += 1

        return chunks

    def _blocks(self, document: ParsedDocument) -> list[tuple[list[str], str, int]]:
        """Les blocs à découper : ``(chemin, texte, offset dans le contenu)``.

        Le curseur ne recule jamais : deux blocs au texte identique reçoivent des offsets
        DIFFÉRENTS. Chercher depuis zéro à chaque fois les aurait fait pointer au même
        endroit — une collision silencieuse dans les métadonnées de chunks distincts.

        Sans section déclarée, le document entier est UN bloc : la découpe à taille fixe
        n'est pas un mode à part, c'est le cas particulier où la structure est muette.
        """
        sections = document.structure.get("sections", [])
        if not sections:
            return [([], document.content, 0)]

        blocks: list[tuple[list[str], str, int]] = []
        cursor = 0

        for section in sections:
            text = section.get("text", "")
            if not text.strip():
                continue

            start = document.content.find(text, cursor)
            if start < 0:
                # L'invariant du parser est rompu : la section n'est pas un morceau
                # littéral du contenu. Poser un offset faux désignerait le mauvais
                # passage sans que rien ne le signale — on préfère n'en poser aucun.
                continue

            cursor = start + len(text)
            blocks.append((list(section.get("path", [])), text, start))

        return blocks or [([], document.content, 0)]

    def _chunk(  # noqa: PLR0913 — l'identité d'un chunk : sa place, son texte, ses bornes
        self,
        document: ParsedDocument,
        *,
        ordinal: int,
        text: str,
        path: list[str],
        char_start: int,
        char_end: int,
    ) -> Chunk:
        return Chunk(
            # Le chunk_id DÉRIVE de l'identifiant du parent : c'est ce qui garantit que
            # deux sagas travaillant sur des documents distincts ne peuvent pas se
            # marcher dessus sur un même chunk (§11 — la garantie vient de la partition,
            # pas d'un verrou).
            chunk_id=f"{document.identifier.raw}_{ordinal:04d}",
            parent_identifier=document.identifier,
            owner_id=document.owner_id,
            ordinal=ordinal,
            text=text,
            tag_path=path,
            char_start=char_start,
            char_end=char_end,
            metadata=document.metadata,
        )


def _windows(length: int, size: int, overlap: int) -> list[tuple[int, int]]:
    """Les fenêtres ``(début, fin)`` couvrant ``length``, avec chevauchement.

    Un bloc plus court que ``size`` donne une fenêtre unique — pas de découpe inutile,
    et surtout pas de fenêtre vide en fin de parcours.
    """
    if length <= size:
        return [(0, length)]

    step = size - overlap
    return [(start, min(start + size, length)) for start in range(0, length, step)]
