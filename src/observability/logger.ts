export function logInfo(message: string, ...args: unknown[]) {
  console.info(`[INFO] ${new Date().toISOString()} - ${message}`, ...args);
}

export function logError(message: string, ...args: unknown[]) {
  console.error(`[ERROR] ${new Date().toISOString()} - ${message}`, ...args);
}
