import type { EnvironmentReport } from '../config';
import { logger } from './logger';

/**
 * Une variable obligatoire absente est journalisée en erreur sans arrêter le
 * démarrage : la fonctionnalité qui en dépend échoue à l'usage.
 */
export const checkEnvironment = (report: EnvironmentReport): void => {
  if (report.missingRequired.length > 0) {
    logger.error(`Critical env vars missing: ${report.missingRequired.join(', ')}`);
  }
  if (report.defaulted.length > 0) {
    logger.warn(`Env vars using fallbacks: ${report.defaulted.join(', ')}`);
  }
  if (report.missingRequired.length === 0) {
    logger.info('Environment configured');
  }
};
