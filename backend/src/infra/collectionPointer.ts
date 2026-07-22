/**
 * Quelle collection Qdrant fait foi ?
 *
 * Le pipeline nomme ses collections par une EMPREINTE de sa config (`9424808d…`) : deux
 * configs produisent deux collections qui coexistent — c'est la condition de l'A/B. Le
 * backend, lui, lisait `QDRANT_COLLECTION` : un nom écrit à la main, qui ne correspondait
 * à aucune empreinte, et qui ne pointait donc sur RIEN.
 *
 * Le pipeline publie désormais un pointeur dans Mongo (`meta_published_collection`), et
 * **seul un run `ok` le met à jour** : un run qui a perdu des documents ne publie pas, et
 * le serving continue de servir le dernier corpus complet.
 *
 * Le fallback sur `QDRANT_COLLECTION` reste — mais il est BRUYANT et VÉRIFIÉ. Un fallback
 * silencieux vers un nom qui n'existe pas reproduirait exactement le défaut qu'on corrige :
 * le backend démarrerait, croirait avoir un corpus, et échouerait à la première question.
 */

import { QdrantClient } from '@qdrant/qdrant-js';
import { getMongoClient } from './mongodb';
import { logger } from '../utils/logger';

const log = logger.child({ context: 'collectionPointer' });

const META_DB = process.env.MONGODB_META_DATABASE || 'MURPHY_META';
const POINTER_COLLECTION = 'meta_published_collection';
const POINTER_KEY = 'current';

export interface PublishedCollection {
  collection_name: string;
  fingerprint: string;
  run_id: string;
  document_count: number;
  published_at: string;
}

/**
 * Lit le pointeur publié par le dernier run `ok`. `null` = aucun run n'a encore publié —
 * ce n'est pas une erreur, c'est un système qui n'a pas encore ingéré.
 */
export async function readPublishedCollection(): Promise<PublishedCollection | null> {
  // `getMongoDb()` rend la base de DONNÉES (LEGIFRANCE) ; le pointeur vit dans la base
  // de MÉTA. On passe donc par le client, qui seul permet d'en changer.
  const client = await getMongoClient();
  const doc = await client
    .db(META_DB)
    .collection<PublishedCollection>(POINTER_COLLECTION)
    .findOne({ key: POINTER_KEY });
  return doc ?? null;
}

/**
 * Résout la collection à interroger, et REFUSE de démarrer sur une collection absente.
 *
 * L'ordre est délibéré :
 *   1. le pointeur (la vérité, publiée par un run complet) ;
 *   2. à défaut, `QDRANT_COLLECTION` — mais en le disant fort ;
 *   3. dans les deux cas, on VÉRIFIE que la collection existe vraiment.
 *
 * L'étape 3 est celle qui compte. Sans elle, le fallback rejouerait le bug d'origine :
 * un nom plausible, aucun vecteur derrière, et la panne repoussée jusqu'à la première
 * question d'un utilisateur — au moment le plus coûteux pour la découvrir.
 */
export async function resolveCollection(qdrantUrl: string): Promise<string> {
  const published = await readPublishedCollection().catch((error) => {
    log.warn({ error: String(error) }, 'Pointeur de collection illisible (Mongo)');
    return null;
  });

  let collection: string;

  if (published) {
    collection = published.collection_name;
    log.info(
      {
        collection,
        runId: published.run_id,
        documentCount: published.document_count,
        publishedAt: published.published_at,
      },
      'Collection résolue depuis le pointeur publié'
    );
  } else {
    collection = process.env.QDRANT_COLLECTION || 'chunks';
    log.warn(
      { collection },
      "Aucun run n'a publié de collection : repli sur QDRANT_COLLECTION. " +
        "Ce nom n'est vérifié par personne — lancer une ingestion complète le remplacera."
    );
  }

  await assertCollectionExists(qdrantUrl, collection);
  return collection;
}

/**
 * Une collection nommée mais absente est un MENSONGE — et il vaut mieux le découvrir au
 * boot que sur la première question d'un utilisateur.
 */
async function assertCollectionExists(qdrantUrl: string, collection: string): Promise<void> {
  const client = new QdrantClient({ url: qdrantUrl });

  const exists = await client.collectionExists(collection).catch((error) => {
    throw new Error(
      `Qdrant injoignable (${qdrantUrl}) : impossible de vérifier la collection ` +
        `« ${collection} ». Cause : ${String(error)}`
    );
  });

  if (!exists.exists) {
    throw new Error(
      `La collection Qdrant « ${collection} » n'existe pas. Le backend ne peut rien ` +
        `retrouver. Lancer une ingestion (kedro run) : un run complet publiera la ` +
        `collection à servir.`
    );
  }

  const info = await client.getCollection(collection);
  log.info(
    { collection, vectors: info.points_count },
    'Collection Qdrant vérifiée — elle existe et contient des vecteurs'
  );

  if (!info.points_count) {
    log.warn({ collection }, 'La collection existe mais est VIDE : aucune source ne remontera');
  }
}
