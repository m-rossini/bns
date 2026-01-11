export function logInfo(message: string, ...args: unknown[]) {
  const prefix = `[INFO] ${new Date().toISOString()} - ${message}`;
  if (typeof console !== 'undefined') {
    if (typeof console.info === 'function') {
      console.info(prefix, ...args);
    } else if (typeof console.log === 'function') {
      console.log(prefix, ...args);
    }
  }
}

export function logError(message: string, ...args: unknown[]) {
  const prefix = `[ERROR] ${new Date().toISOString()} - ${message}`;
  if (typeof console !== 'undefined') {
    if (typeof console.error === 'function') {
      console.error(prefix, ...args);
    } else if (typeof console.log === 'function') {
      console.log(prefix, ...args);
    }
  }
}
