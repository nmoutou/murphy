/** Une ellipse avant la page courante, une après : chacune est unique, et sert de clé */
export type PageItem = number | 'ellipsis-before' | 'ellipsis-after';

const FIRST_PAGE = 1;
const NEIGHBOUR_DISTANCE = 1;
// Une ellipse prendrait la place d'une seule page cachée : autant afficher la page
const SMALLEST_HIDDEN_GAP = 2;

/** La première et la dernière page, la page courante et ses voisines ; une ellipse par trou */
export const buildPageItems = (page: number, pageCount: number): PageItem[] => {
  const shownPages = [FIRST_PAGE, page - NEIGHBOUR_DISTANCE, page, page + NEIGHBOUR_DISTANCE]
    .concat(pageCount)
    .filter((shown) => shown >= FIRST_PAGE && shown <= pageCount);
  const sortedPages = [...new Set(shownPages)].sort((left, right) => left - right);
  return sortedPages.flatMap((shown, index): PageItem[] => {
    const previous = sortedPages[index - 1];
    if (previous === undefined) return [shown];
    const gap = shown - previous - 1;
    if (gap >= SMALLEST_HIDDEN_GAP)
      return [shown <= page ? 'ellipsis-before' : 'ellipsis-after', shown];
    return gap > 0 ? [previous + 1, shown] : [shown];
  });
};
