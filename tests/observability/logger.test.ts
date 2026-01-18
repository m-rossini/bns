// Moved from tests/logger.test.ts
// Updated imports to reflect new file paths
import { describe, it, expect } from 'vitest';
import { logInfo, logError } from '@/observability/logger';

describe('Logger', () => {
  it('should log info without throwing', () => {
    expect(() => logInfo('Test info')).not.toThrow();
  });
  it('should log error without throwing', () => {
    expect(() => logError('Test error')).not.toThrow();
  });
});