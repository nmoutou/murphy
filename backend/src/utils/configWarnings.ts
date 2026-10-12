import type { EnvironmentReport } from '../config';
import { logger } from './logger';

/**
 * Fail-fast (ADR-010) : une variable obligatoire absente arrête le démarrage, plutôt
 * qu'une fonctionnalité qui échouerait à l'usage.
 * @throws en nommant les variables obligatoires absentes
 */
export const checkEnvironment = (report: EnvironmentReport): void => {
  if (report.defaulted.length > 0) {
    logger.warn(`Env vars using fallbacks: ${report.defaulted.join(', ')}`);
  }
  if (report.missingRequired.length > 0) {
    throw new Error(`Critical env vars missing: ${report.missingRequired.join(', ')}`);
  }
  logger.info('Environment configured');
};
