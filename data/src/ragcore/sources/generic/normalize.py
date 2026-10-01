"""La normalisation typographique : invisible à l'œil, visible au modèle d'embedding.

``é`` composé ou décomposé, espaces insécables ou fines, caractères de largeur nulle :
autant de variantes qu'un tokenizer distingue. On normalise la typographie, jamais la
langue : ni lemmatisation, ni minuscules, ni mots vides.

La modifier invalide les vecteurs déjà écrits : tout le corpus se réingère.
"""

from __future__ import annotations

import re
import unicodedata

__all__ = ["normalize_text"]

_TAGS = re.compile(r"<[^>]+>")
"""Du HTML échappé survit dans le texte de certains nœuds, et finirait à l'écran."""

# En échappements, jamais en littéral : un caractère invisible est illisible en diff
# (ruff PLE2515)
_SPACES = re.compile(
    "[ \t"
    "\u00a0"  # insécable — omniprésente dans le XML juridique
    "\u202f"  # fine insécable (« article 3 »)
    "\u2000-\u200a"  # espaces typographiques : cadratin, demi-cadratin, fine…
    "\u205f"  # espace mathématique moyenne
    "\u3000"  # idéographique
    "]+"
)
"""Toutes les espaces horizontales, ramenées à une espace ordinaire pour que le
tokenizer sépare les mots."""

_ZERO_WIDTH = re.compile(
    "["
    "\u200b"  # espace de largeur nulle
    "\u200c\u200d"  # non-jointeur / jointeur de largeur nulle
    "\ufeff"  # BOM égaré en milieu de texte
    "\u00ad"  # césure conditionnelle (soft hyphen)
    "]"
)
"""Invisibles, et pourtant tokenisés : le ``\\u00ad`` coupe un mot en deux pour le
modèle."""

_BLANK_LINES = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    """L'ordre compte : NFC d'abord, sinon des accents combinants restent orphelins ;
    largeur nulle avant les espaces, sinon un ``\\u200b`` souderait deux mots.
    """
    if not text:
        return ""

    # NFC, comme le web et les modèles d'embedding entraînés dessus
    normalized = unicodedata.normalize("NFC", str(text))

    normalized = _TAGS.sub(" ", normalized)
    normalized = _ZERO_WIDTH.sub("", normalized)
    normalized = _SPACES.sub(" ", normalized)
    normalized = _BLANK_LINES.sub("\n\n", normalized)

    # L'indentation XML n'est pas du contenu
    return "\n".join(line.strip() for line in normalized.split("\n")).strip()
