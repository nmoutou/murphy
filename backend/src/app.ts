import express, { Application } from 'express';
import { errorHandler, notFoundHandler } from './middleware/errorHandler';
import { requestLogger } from './middleware/requestLogger';
import { helm, limiter, originParser } from "./middleware/security"
import { buildApiResponse } from './utils/response';
import chatRouter from './routes/chat';
import healthRouter from './routes/health';
import documentsRouter from './routes/documents';
const app: Application = express();

// Request logging (before other middleware)
app.use(requestLogger);

// Security middleware
app.use(helm);
app.use(limiter);

// Body parsing middleware
app.use(originParser);
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Routes
app.get('/api/v1', (_req, res) => {
  res.json(buildApiResponse(200, 'OK', {
    name: 'Murphy API',
    version: '1.0.0',
    env: process.env.NODE_ENV || 'development',
  }));
});

// Health check endpoint
app.use('/api/v1/health', healthRouter);

// Chat route for RAG-powered streaming
app.use('/api/v1/chat', chatRouter);

// Documents search endpoint
app.use('/api/v1/documents', documentsRouter);

// Error handling (must be last)
app.use(notFoundHandler);
app.use(errorHandler);

export default app;
