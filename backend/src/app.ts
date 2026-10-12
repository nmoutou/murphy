import express, { Application } from 'express';
import { errorHandler, notFoundHandler } from './middleware/errorHandler';
import { requestLogger } from './middleware/requestLogger';
import { helm, limiter, originParser } from "./middleware/security"
import { buildApiResponse } from './utils/response';
import { config } from './config';
import documentsRouter from './routes/documents';
import explanationsRouter from './routes/explanations';
import healthRouter from './routes/health';
import searchRouter from './routes/search';
import { HTTP_STATUS } from './utils/httpStatus';
import { MAX_REQUEST_BODY_BYTES, toExplanationBodyLimit } from './utils/requestLimits';

// Pas encore de reverse proxy : `req.ip` est l'adresse de la socket, un
// `X-Forwarded-For` forgé ne contourne pas les limites. Derrière un proxy, mettre ici
// le nombre de sauts.
const TRUST_PROXY = false;
const EXPLANATIONS_PATH = '/api/v1/explanations';

const app: Application = express();
app.set('trust proxy', TRUST_PROXY);

app.use(requestLogger);

app.use(helm);
app.use(limiter);

app.use(originParser);
// Avant le parseur général, qui saute un corps déjà lu
app.use(EXPLANATIONS_PATH, express.json({ limit: toExplanationBodyLimit(config.llm.contextMaxChars) }));
app.use(express.json({ limit: MAX_REQUEST_BODY_BYTES }));

app.get('/api/v1', (_req, res) => {
  res.json(buildApiResponse(HTTP_STATUS.OK, 'OK', {
    name: 'Murphy API',
    version: '1.0.0',
    env: config.server.nodeEnv,
  }));
});

app.use('/api/v1/health', healthRouter);

app.use('/api/v1/search', searchRouter);
app.use('/api/v1/documents', documentsRouter);
app.use(EXPLANATIONS_PATH, explanationsRouter);

// Toujours en dernier
app.use(notFoundHandler);
app.use(errorHandler);

export default app;
