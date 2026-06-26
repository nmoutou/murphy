import { AppError, asyncHandler } from '../../middleware/errorHandler';
import { Request, Response, NextFunction } from 'express';

describe('Error Handler Middleware', () => {
  describe('AppError', () => {
    it('should create an operational error with correct properties', () => {
      const error = new AppError('Test error', 400, 'TEST_ERROR');
      
      expect(error.message).toBe('Test error');
      expect(error.statusCode).toBe(400);
      expect(error.code).toBe('TEST_ERROR');
      expect(error.isOperational).toBe(true);
      expect(error).toBeInstanceOf(Error);
      expect(error).toBeInstanceOf(AppError);
    });

    it('should default to 500 status and INTERNAL_ERROR code', () => {
      const error = new AppError('Something went wrong');
      
      expect(error.statusCode).toBe(500);
      expect(error.code).toBe('INTERNAL_ERROR');
      expect(error.isOperational).toBe(true);
    });
  });

  describe('asyncHandler', () => {
    it('should call the async function and pass to next on error', async () => {
      const mockReq = {} as Request;
      const mockRes = {} as Response;
      const mockNext = jest.fn() as NextFunction;
      
      const asyncFn = jest.fn().mockRejectedValue(new Error('Async error'));
      const handler = asyncHandler(asyncFn);
      
      await handler(mockReq, mockRes, mockNext);
      
      expect(asyncFn).toHaveBeenCalledWith(mockReq, mockRes, mockNext);
      expect(mockNext).toHaveBeenCalledWith(expect.any(Error));
    });

    it('should not call next if async function succeeds', async () => {
      const mockReq = {} as Request;
      const mockRes = {} as Response;
      const mockNext = jest.fn() as NextFunction;
      
      const asyncFn = jest.fn().mockResolvedValue('success');
      const handler = asyncHandler(asyncFn);
      
      await handler(mockReq, mockRes, mockNext);
      
      expect(asyncFn).toHaveBeenCalledWith(mockReq, mockRes, mockNext);
      expect(mockNext).not.toHaveBeenCalled();
    });
  });
});
