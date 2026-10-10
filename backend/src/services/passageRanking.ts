/** Les passages d'un document trouvé (ADR-028 §7) */

import type { PassageRef, RetrievedDocument, SearchHit } from '../types/rag';

/** La constante du RRF d'OpenSearch : les deux fusions classent de la même façon */
const RRF_RANK_CONSTANT = 60;

interface FusedPassage {
  readonly ref: PassageRef;
  readonly score: number;
}

/** Dédoublonnées par `chunkId` ; à score égal, l'ordre d'apparition (le tri est stable) */
const fuseByRank = (rankings: readonly (readonly PassageRef[])[]): PassageRef[] => {
  const fused = new Map<string, FusedPassage>();
  for (const ranking of rankings) {
    ranking.forEach((ref, index) => {
      const previous = fused.get(ref.chunkId);
      const score = (previous?.score ?? 0) + 1 / (RRF_RANK_CONSTANT + index + 1);
      fused.set(ref.chunkId, { ref: previous?.ref ?? ref, score });
    });
  }
  return [...fused.values()].sort((left, right) => right.score - left.score).map(({ ref }) => ref);
};

/**
 * Les passages lexicaux et vectoriels, fusionnés par RRF sur leurs rangs. Un document
 * trouvé par son titre ou ses métadonnées n'en a aucun : son texte se lit à la demande
 * (ADR-031 §3).
 */
export const toRetrievedDocument = (hit: SearchHit): RetrievedDocument => {
  return {
    identifier: hit.identifier,
    documentType: hit.documentType,
    nature: hit.nature,
    passages: fuseByRank([hit.lexicalPassages, hit.vectorPassages]),
  };
};
