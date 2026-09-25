"""La normalisation typographique — **§4, qui n'existait pas**.

**Ce qu'elle fait, et pourquoi elle compte pour un moteur de recherche.** Le même mot
peut s'écrire de plusieurs façons qu'aucun humain ne distingue et qu'aucune machine ne
confond :

- ``é`` peut être **un** caractère (U+00E9) ou **deux** (``e`` + accent combinant U+0301).
  Les deux s'affichent identiquement. Pour un tokenizer, ce sont deux mots différents —
  et une requête écrite d'une façon ne trouvera jamais un document écrit de l'autre.
- Les espaces insécables (U+00A0) et fines (U+202F) abondent dans le XML juridique
  (« article 3 », « 15 000 € »). Un tokenizer qui ne les reconnaît pas colle les mots.
- Les caractères de largeur nulle sont invisibles à l'écran et bien réels pour le modèle.

Rien de tout cela n'est visible à l'œil. Tout est visible au modèle d'embedding.

**Ce qu'elle NE fait PAS, et c'est délibéré (§4).** Aucune lemmatisation, aucun retrait
de mots vides, aucune mise en minuscules, aucune linéarisation. Ce qui sort d'ici est du
français lisible — pas un sac de lemmes. On normalise la *typographie*, jamais la
*langue* : la première est du bruit d'encodage, la seconde est du sens.

**⚠️ Elle entre dans le hash (§6).** ``formatting.normalization.version`` peuple le
``WorkflowConfig``, donc le nom de la collection Qdrant. Faire passer cette version de
``none`` à ``v1`` **crée mécaniquement une nouvelle collection** : les vecteurs d'avant et
d'après ne sont pas comparables et ne doivent pas cohabiter. C'est exactement le
comportement voulu — et le premier vrai exercice de l'A/B que le fingerprint rend possible.
"""

from __future__ import annotations

import re
import unicodedata

__all__ = ["NORMALIZATION_VERSION", "normalize_text"]

NORMALIZATION_VERSION = "v1"
"""La version de CE traitement. Elle doit être reportée dans ``parameters.yml``.

Changer le code sans changer la version produirait deux jeux de vecteurs incomparables
**dans la même collection**, sans que rien ne le signale. La version est le lien entre le
traitement et le hash qui nomme la collection — la rompre, c'est rouvrir précisément le
trou que §6 ferme.
"""


_TAGS = re.compile(r"<[^>]+>")
"""Les balises résiduelles : du HTML échappé survit dans le TEXTE de certains nœuds, et
ressortirait tel quel dans Mongo — donc à l'écran de l'utilisateur."""

# Les caractères sont écrits en ÉCHAPPEMENTS, jamais en littéral. Un caractère invisible
# collé dans le source est irrelisible, illisible en diff, et se perd au premier
# copier-coller. Ce qui décide du découpage des mots ne doit pas être invisible dans le
# fichier qui en décide.
_SPACES = re.compile(
    "[ \t"
    "\u00a0"  # insécable — omniprésente dans le XML juridique
    "\u202f"  # fine insécable (« article 3 »)
    "\u2000-\u200a"  # espaces typographiques : cadratin, demi-cadratin, fine…
    "\u205f"  # espace mathématique moyenne
    "\u3000"  # idéographique
    "]+"
)
"""Toutes les espaces horizontales, y compris insécables et fines.

**Écrites en échappements Unicode, jamais en littéral.** Un caractère invisible collé dans
le source est irrelisible, illisible en diff, et se perd au premier copier-coller. Ce qui
décide du découpage des mots ne doit pas être invisible dans le fichier qui en décide —
``ruff`` l'exige d'ailleurs (règle ``PLE2515``), et il avait raison contre moi.

Les ramener à une espace ordinaire est ce qui permet au tokenizer de voir des mots là où il
voyait un seul bloc — le gain le plus concret de ce module.
"""

_ZERO_WIDTH = re.compile(
    "["
    "\u200b"  # espace de largeur nulle
    "\u200c\u200d"  # non-jointeur / jointeur de largeur nulle
    "\ufeff"  # BOM égaré en milieu de texte
    "\u00ad"  # césure conditionnelle (soft hyphen)
    "]"
)
"""Largeur nulle et césures conditionnelles : invisibles, et pourtant tokenisés.

Le ``\\u00ad`` (soft hyphen) est le pire : il coupe un mot en deux pour le modèle sans
qu'on voie quoi que ce soit à l'écran.
"""

_BLANK_LINES = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    """Normalise la typographie d'un texte. **Ne touche pas à la langue.**

    L'ordre des opérations n'est pas indifférent :

    1. **NFC d'abord** — recompose ``e`` + accent combinant en ``é``. Le faire après le
       nettoyage des espaces laisserait des accents combinants orphelins aux coupures.
    2. Retrait des balises résiduelles.
    3. Retrait des caractères de largeur nulle, **avant** l'espacement : un ``\\u200b``
       entre deux mots empêcherait sinon de les voir comme séparés.
    4. Unification des espaces, puis des lignes vides.
    """
    if not text:
        return ""

    # NFC : une seule représentation par caractère. Le choix de NFC (et non NFD) est celui
    # de tout l'écosystème web et des modèles d'embedding entraînés dessus.
    normalized = unicodedata.normalize("NFC", str(text))

    normalized = _TAGS.sub(" ", normalized)
    normalized = _ZERO_WIDTH.sub("", normalized)
    normalized = _SPACES.sub(" ", normalized)
    normalized = _BLANK_LINES.sub("\n\n", normalized)

    # Chaque ligne perd ses espaces de bord : une indentation XML de huit espaces n'est pas
    # du contenu, et elle traverserait sinon jusque dans l'embedding.
    return "\n".join(line.strip() for line in normalized.split("\n")).strip()
