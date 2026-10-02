# ADR-017 — Erreurs du chat : une modale, l'étape en cause, un arrêt propagé au backend

**Statut** : ✅ Accepté (26 septembre 2026)

## Contexte

Quand une étape du pipeline échoue (TEI, Qdrant, Mongo ou le LLM), l'utilisateur ne voit
rien : la bulle de l'IA reste vide et `…` cesse de clignoter. Le backend envoie
bien une part `{ type: 'error', errorText }`, que `useChat` convertit en `error`, mais
`useRagChat` ne l'expose pas.

L'examen du chemin d'erreur relève trois autres défauts :

- **L'étape en cause est perdue.** Le backend la connaît (`RagError.stage` :
  `embedding`, `retrieval` ou `llm`), mais `errorText` ne porte que le message brut.
- **Le message brut part au client.** `onError` renvoie `err.message`, par exemple
  `Failed to search Qdrant: connect ECONNREFUSED …` : des détails internes sans intérêt
  pour l'utilisateur.
- **L'arrêt ne remonte pas au backend.** Fermer le WebSocket annule la lecture du flux
  (`reader.cancel()`), mais `createUIMessageStream` n'interrompt pas `execute` : ses
  écritures sont avalées en silence, et le LLM continue de générer jusqu'au bout. Le
  bouton d'arrêt du `ChatBox` a le même défaut aujourd'hui.

## Décision

**1. Une modale générique.** Un composant `Modal` affiche un contenu quelconque
(`children`) au-dessus de la page, dont le fond est grisé. Il s'appuie sur l'élément
natif `<dialog>` et `showModal()`, qui fournissent le fond (`::backdrop`), l'inertie de la
page, le piège de focus, la fermeture par Échap et le rôle accessible. `Modal` porte un
titre et un bouton de fermeture doté d'un nom accessible. Son premier contenu est
`ErrorDialog`. Les erreurs, les informations et les panneaux (réglages, sous-menus)
viendront s'y loger. Un menu ancré à un bouton n'est pas une modale : il relèvera de
l'attribut `popover`.

**2. Une erreur structurée dans le contrat.** Un nouveau module
`@murphy/contract/errors` définit `chatErrorSchema` :
`{ stage: 'request' | 'embedding' | 'retrieval' | 'llm' | 'internal', code: string }`.
Le backend sérialise cet objet en JSON dans `errorText`, à la place du message brut, et
journalise le détail. Le frontend relit `error.message` avec ce schéma. Un texte qui ne
s'y conforme pas, par exemple une connexion impossible, donne l'étape `connection`,
propre au frontend.

**3. La modale nomme l'étape en cause.** Par exemple : « La recherche des sources a
échoué. » `retrieval` couvre Qdrant et la lecture des documents dans Mongo. Le `code`
et le message complet partent dans `console.error`. La modale n'offre pas de bouton
« Réessayer » : l'utilisateur repose sa question.

**4. Après une erreur, la bulle de l'IA disparaît.** `useRagChat` retire le dernier
message de l'assistant (`setMessages`) et ferme le WebSocket s'il est encore ouvert. Le
message de l'utilisateur reste affiché. Fermer la modale efface l'erreur
(`clearError`).

**5. L'arrêt est propagé au backend.** La fermeture du socket (et celle de la requête
HTTP pour `/streams`) déclenche un `AbortController`. `createChatStream` reçoit son
signal et le vérifie entre les étapes, et `llm.stream` le transmet à son `fetch`. Un
flux interrompu n'envoie pas de part `error`, puisque le client est parti. Le bouton
d'arrêt du `ChatBox` en bénéficie aussi.

## Alternatives rejetées

- **Afficher l'erreur sous le dernier message**, première forme de la décision :
  écartée par le porteur au profit d'une modale.
- **Une bibliothèque de dialogue** (Radix, Headless UI) : `<dialog>` couvre le besoin
  sans dépendance.
- **Un gestionnaire global de modales** (contexte, pile, registre de types) : un seul
  composant ouvre une modale aujourd'hui. Le contexte viendra avec le deuxième, s'il est
  éloigné du premier.
- **Une part `data-error`** : elle s'attache au message de l'assistant, que l'on
  retire, et `useChat` ne passerait pas en `status === 'error'`.
- **Garder le message brut et y chercher l'étape** : cela fige un format de texte sans
  contrat, et laisse fuir les détails internes.

## Conséquences

- **Contrat** : un deuxième sous-chemin, `@murphy/contract/errors` (`exports` et
  `typesVersions`). Les images de dev sont à reconstruire (`npm run build` puis
  `npm run up`). `RagStage` du backend en dérive.
- **Backend** : `chatService` (signal, sérialisation de l'erreur), `chatWebSocket` et
  `routes/chat.ts` (erreurs de requête et de quota avec l'étape `request`, fermeture
  reliée au signal), `infra/llm.ts` (signal transmis au `fetch`). La route
  `/completions` renvoie désormais l'erreur structurée. Tests : la sérialisation et
  l'arrêt entre les étapes.
- **Frontend** : `components/ui/Modal.tsx` et `ErrorDialog.tsx` apparaissent,
  `ErrorMessage.tsx` et la détection du préfixe « ❌ » disparaissent. `useRagChat`
  expose l'erreur et fiabilise le transport. Les couleurs dont la modale a
  besoin sont déclarées dans le `@theme` de `globals.css`, pour ne pas
  écrire un nouveau composant en styles inline.
- Deux défauts du backend sont ouverts et réglés par ce lot : l'arrêt non propagé et le
  message brut envoyé au client.

## Références

ADR-016 (dépôt unique, contrat partagé) · `backend/src/types/rag.ts` (`RagError`) ·
`packages/contract/src/messages.ts`
