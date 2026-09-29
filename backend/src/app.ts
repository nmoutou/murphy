import express, { Application } from 'express';
import { errorHandler, notFoundHandler } from './middleware/errorHandler';
import { requestLogger } from './middleware/requestLogger';
import { helm, limiter, originParser } from "./middleware/security"
import { buildApiResponse } from './utils/response';
import { config } from './config';
import chatRouter from './routes/chat';
import healthRouter from './routes/health';
import { HTTP_STATUS } from './utils/httpStatus';
import { MAX_REQUEST_BODY_BYTES } from './utils/requestLimits';

// No reverse proxy in front of the backend yet (not deployed): `req.ip`
// is the socket address, so a forged `X-Forwarded-For` cannot dodge the rate
// limits. Behind a proxy, set the number of proxy hops here.
const TRUST_PROXY = false;

const app: Application = express();
app.set('trust proxy', TRUST_PROXY);

// Request logging (before other middleware)
app.use(requestLogger);

// Security middleware
app.use(helm);
app.use(limiter);

// Body parsing middleware
app.use(originParser);
app.use(express.json({ limit: MAX_REQUEST_BODY_BYTES }));

// Routes
app.get('/api/v1', (_req, res) => {
  res.json(buildApiResponse(HTTP_STATUS.OK, 'OK', {
    name: 'Murphy API',
    version: '1.0.0',
    env: config.server.nodeEnv,
  }));
});

// Health check endpoint
app.use('/api/v1/health', healthRouter);

// Chat route for RAG-powered streaming
app.use('/api/v1/chat', chatRouter);

// Error handling (must be last)
app.use(notFoundHandler);
app.use(errorHandler);

export default app;
