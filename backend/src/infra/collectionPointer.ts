/**
 * Quelle collection Qdrant fait foi, et dans quel format ?
 *
 * Le pipeline nomme ses collections par une EMPREINTE de sa config (`9424808d…`) : deux
 * configs produisent deux collections qui coexistent — c'est la condition de l'A/B. Le
 * pipeline publie donc un pointeur dans Mongo (`meta_published_collection`), et **seul un
 * run `ok` le met à jour** : un run qui a perdu des documents ne publie pas, et le serving
 * continue de servir le dernier corpus complet.
 *
 * Le pointeur porte aussi la version du contrat ingestion ↔ serving que la collection
 * respecte (ADR-039). Le backend REFUSE de démarrer sans pointeur, sur une autre version,
 * ou sur une collection absente : une collection que personne n'a publiée n'a pas de
 * format connu, et la servir reviendrait à découvrir l'écart sur la première question.
 */

import { QdrantClient } from '@qdrant/qdrant-js';
import type { MongoClient } from 'mongodb';
import type { QdrantConfig } from '../config';
import { logger as rootLogger } from '../utils/logger';

const logger = rootLogger.child({ context: 'collectionPointer' });

const POINTER_COLLECTION = 'meta_published_collection';
const POINTER_KEY = 'current';
const FULL_RUN_COMMAND = 'kedro run --params source=all';

/**
 * La version du contrat que ce code lit (ADR-039 §2) : payload Qdrant, Mongo
 * `documents`, pointeur. Même valeur que `SERVING_CONTRACT_VERSION` côté `data/`
 * (`ragcore/core/models/published_collection.py`) : les deux changent ensemble.
 */
export const SERVING_CONTRACT_VERSION = 1;

export interface PublishedCollection {
  collection_name: string;
  fingerprint: string;
  run_id: string;
  document_count: number;
  published_at: string;
  /** Absent d'un pointeur publié avant l'ADR-039 */
  serving_contract_version?: number;
}

export interface CollectionSources {
  readonly mongoClient: MongoClient;
  /** The database holding the pointer — not the data database */
  readonly metaDatabase: string;
  readonly qdrant: QdrantConfig;
}

/**
 * Lit le pointeur publié par le dernier run `ok`. `null` = aucun run n'a encore publié —
 * ce n'est pas une erreur, c'est un système qui n'a pas encore ingéré.
 */
export async function readPublishedCollection(
  mongoClient: MongoClient,
  metaDatabase: string
): Promise<PublishedCollection | null> {
  // Le pointeur vit dans la base de MÉTA, pas dans celle des DONNÉES (LEGIFRANCE) :
  // on passe donc par le client, qui seul permet de changer de base.
  const doc = await mongoClient
    .db(metaDatabase)
    .collection<PublishedCollection>(POINTER_COLLECTION)
    .findOne({ key: POINTER_KEY });
  return doc ?? null;
}

/**
 * Résout la collection à interroger, et REFUSE de démarrer si elle n'est pas servable :
 * pas de pointeur, une version du contrat inconnue, ou une collection absente de Qdrant.
 * Mieux vaut le découvrir au boot que sur la première question d'un utilisateur.
 */
export async function resolveCollection(sources: CollectionSources): Promise<string> {
  const collection = await readServableCollection(sources);
  await assertCollectionExists(sources.qdrant, collection);
  return collection;
}

async function readServableCollection(sources: CollectionSources): Promise<string> {
  const published = await readPublishedCollection(sources.mongoClient, sources.metaDatabase).catch((error) => {
    throw new Error(
      `Pointeur de collection illisible (${sources.metaDatabase}.${POINTER_COLLECTION}). Cause : ${String(error)}`
    );
  });

  if (!published) {
    throw new Error(
      `Aucun run d'ingestion n'a publié de collection (${sources.metaDatabase}.${POINTER_COLLECTION}). ` +
        `Lancer un run complet : ${FULL_RUN_COMMAND}.`
    );
  }
  assertContractVersion(published);

  logger.info(
    {
      collection: published.collection_name,
      runId: published.run_id,
      documentCount: published.document_count,
      publishedAt: published.published_at,
      servingContractVersion: published.serving_contract_version,
    },
    'Collection résolue depuis le pointeur publié'
  );
  return published.collection_name;
}

/**
 * Une version plus ancienne se corrige en réingérant, une plus récente en mettant le
 * backend à jour. Un pointeur sans version date d'avant le contrat : réingérer.
 */
function assertContractVersion(published: PublishedCollection): void {
  const version = published.serving_contract_version;
  if (version === SERVING_CONTRACT_VERSION) return;

  const remedy =
    version !== undefined && version > SERVING_CONTRACT_VERSION
      ? 'Mettre à jour le backend.'
      : `Réingérer le corpus : ${FULL_RUN_COMMAND}.`;
  throw new Error(
    `La collection publiée « ${published.collection_name} » suit le contrat de serving ` +
      `v${version ?? '(aucune)'}, ce backend lit la v${SERVING_CONTRACT_VERSION} (ADR-039). ${remedy}`
  );
}

/**
 * Une collection nommée mais absente est un MENSONGE — et il vaut mieux le découvrir au
 * boot que sur la première question d'un utilisateur.
 */
async function assertCollectionExists(qdrant: QdrantConfig, collection: string): Promise<void> {
  const client = new QdrantClient({ url: qdrant.url, timeout: qdrant.timeoutMs });

  const exists = await client.collectionExists(collection).catch((error) => {
    throw new Error(
      `Qdrant injoignable (${qdrant.url}) : impossible de vérifier la collection ` +
        `« ${collection} ». Cause : ${String(error)}`
    );
  });

  if (!exists.exists) {
    throw new Error(
      `La collection Qdrant « ${collection} » n'existe pas, alors que le pointeur la ` +
        `publie. Lancer un run complet : ${FULL_RUN_COMMAND}.`
    );
  }

  const info = await client.getCollection(collection);
  logger.info(
    { collection, vectors: info.points_count },
    'Collection Qdrant vérifiée — elle existe et contient des vecteurs'
  );

  if (!info.points_count) {
    logger.warn({ collection }, 'La collection existe mais est VIDE : aucune source ne remontera');
  }
}
