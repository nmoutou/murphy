import type { EnvironmentReport } from '../config';
import { logger } from './logger';

/**
 * Logs what `loadConfig` found at boot. A missing required variable is logged
 * as an error but does not stop the boot: the feature that needs it fails on use.
 */
export function checkEnvironment(report: EnvironmentReport): void {
  if (report.missingRequired.length > 0) {
    logger.error(`Critical env vars missing: ${report.missingRequired.join(', ')}`);
  }
  if (report.defaulted.length > 0) {
    logger.warn(`Env vars using fallbacks: ${report.defaulted.join(', ')}`);
  }
  if (report.missingRequired.length === 0) {
    logger.info('Environment configured');
  }
}
