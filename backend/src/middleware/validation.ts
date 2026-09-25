import { body, ValidationChain, validationResult } from 'express-validator';
import { Request, Response, NextFunction } from 'express';
import { buildApiResponse } from '../utils/response';

/**
 * Validation middleware that checks for errors and returns 400 if validation fails
 */
export const validationErrorHandler = (req: Request, res: Response, next: NextFunction): void => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    res.status(400).json({
      ...buildApiResponse(400, 'VALIDATION_ERROR'),
      errors: errors.array().map((err) => ({ field: err.type === 'field' ? err.path : undefined, message: err.msg })),
    });
    return;
  }
  next();
};

/**
 * Chat stream request validation
 * Validates the request body for RAG-powered chat streaming
 */
export const chatValidation: ValidationChain[] = [
  body('messages')
    .isArray({ min: 1 })
    .withMessage('messages must be a non-empty array'),

  body('messages.*.role')
    .isString()
    .isIn(['user', 'assistant', 'system'])
    .withMessage('message role must be user, assistant, or system'),

  body('messages.*.parts')
    .isArray()
    .withMessage('parts must be an array'),
];
