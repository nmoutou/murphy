import express from 'express';
import { getMongoDb } from '../infra/mongodb';
import { asyncHandler } from '../middleware/errorHandler';
import { buildApiResponse } from '../utils/response';

const router = express.Router();

router.get('/:eli', asyncHandler(async (req, res) => {
  const { eli } = req.params;
  const db = await getMongoDb();
  const collectionName = process.env.MONGODB_COLLECTION || 'chunks';
  const collection = db.collection(collectionName);

  const docs = await collection.find({ eli }).toArray();

  if (docs.length === 0) {
    res.status(404).json(buildApiResponse(404, 'NOT_FOUND'));
    return;
  }

  res.json(buildApiResponse(200, 'OK', docs.map(doc => ({
    eli: doc.eli,
    type: doc.document_type,
    title: doc.titrefull ?? doc.titre ?? doc.num ?? doc.eli,
    chunk_index: doc.chunk_index ?? null,
  }))));
}));

export default router;
