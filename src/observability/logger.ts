export function logDebug(message: string, ...args: unknown[]) {
  const prefix = `[DEBUG] ${new Date().toISOString()} - ${message}`;
  // console.log("-------------------------------------")
  // console.log(">>>Logging debug message");
  // console.log(">>>Args:", args);
  // console.log(">>>Prefix:", prefix);
  // console.log(">>>Typeof console:", typeof console);
  // console.log(">>>Console object:", console);
  // console.log(">>>Typeof console.debug:", typeof console.debug);
  // console.log(">>>Typeof console.log:", typeof console.log);
  // console.log("-------------------------------------")
  if (typeof console !== 'undefined') {
    if (typeof console.debug === 'function') {
      console.debug(prefix, ...args);
    } else if (typeof console.log === 'function') {
      console.log(prefix, ...args);
    }
  }
}

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

export function logWarn(message: string, ...args: unknown[]) {
  const prefix = `[WARN] ${new Date().toISOString()} - ${message}`;
  if (typeof console !== 'undefined') {
    if (typeof console.warn === 'function') {
      console.warn(prefix, ...args);
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
