"""Les points d'entrée en ligne de commande du harnais.

**La seule couche autorisée à tout connaître** — settings, adapters concrets,
services — et donc la seule qui *compose*. Rien ici ne calcule : le domaine reste
dans ``core/``, les chemins de lecture dans ``adapters/``. Un module de ce paquet
se lit comme un câblage, pas comme une logique.

C'est aussi le seul endroit où ``print`` est légitime (règle ``T201`` levée en
``per-file-ignores``) : une commande parle à un opérateur.
"""
