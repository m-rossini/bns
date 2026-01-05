// logger.test.ts
// TDD: Logger utility tests
import { describe, it, expect } from 'vitest';
import { logInfo, logError } from '../src/logger';

describe('Logger', () => {
  it('should log info without throwing', () => {
    expect(() => logInfo('Test info')).not.toThrow();
  });
  it('should log error without throwing', () => {
    expect(() => logError('Test error')).not.toThrow();
  });
});