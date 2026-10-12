/** Un repère `[n]` que le LLM a écrit, sauf s'il ouvre déjà un lien Markdown `[n](…)` */
const CITATION_PATTERN = /\[(\d+)\](?!\()/g;
const CITATION_HREF_PREFIX = '#source-';
const CITATION_HREF_PATTERN = /^#source-(\d+)$/;

/** Chaque repère devient un lien interne, que le rendu du Markdown transforme en bouton */
export const linkCitations = (markdown: string): string =>
  markdown.replace(CITATION_PATTERN, `[$1](${CITATION_HREF_PREFIX}$1)`);

/** Le numéro d'un repère lié par `linkCitations`, ou `undefined` pour un autre lien */
export const readCitation = (href: string | undefined): number | undefined => {
  const match = href?.match(CITATION_HREF_PATTERN);
  return match ? Number(match[1]) : undefined;
};
